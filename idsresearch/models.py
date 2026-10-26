"""Fixed encoders followed by trainable layers; state is local to each forward."""
import torch
from torch import nn
import snntorch as snn
from snntorch import surrogate


def rate_spikes(x, steps):
    """Deterministic phase-accumulator code; no trainable parameter precedes it."""
    t = torch.arange(steps, device=x.device, dtype=x.dtype)[:, None, None]
    phase = torch.arange(x.shape[-1], device=x.device, dtype=x.dtype)[None, None, :]
    phase = (phase * 0.61803398875).remainder(1)
    return torch.floor((t+1)*x[None]+phase)-torch.floor(t*x[None]+phase)


def temporal_spikes(x, steps):
    index = torch.round((1-x)*(steps-1)).long()
    return (torch.arange(steps, device=x.device)[:, None, None] == index[None]).to(x.dtype)


class FixedEncoder(nn.Module):
    def __init__(self, kind, steps, populations, unit_range=True):
        super().__init__()
        self.kind, self.steps, self.unit_range = kind, steps, unit_range
        self.register_buffer("centres", torch.linspace(0, 1, populations))

    def forward(self, x):
        x = x.clamp(0, 1) if self.unit_range else x.sigmoid()
        if self.kind == "temporal":
            return temporal_spikes(x, self.steps)
        if self.kind == "population":
            width = 1 / (len(self.centres)-1)
            x = torch.exp(-0.5*((x[..., None]-self.centres)/width)**2).flatten(1)
        return rate_spikes(x, self.steps)


class SpikeBranch(nn.Module):
    def __init__(self, features, classes, kind, config):
        super().__init__()
        self.encoder = FixedEncoder(kind, config.steps, config.populations, config.scaler == "quantile")
        size = features * (config.populations if kind == "population" else 1)
        dims = [size, *config.hidden]
        self.linears = nn.ModuleList(nn.Linear(a, b) for a, b in zip(dims, dims[1:]))
        self.norms = nn.ModuleList(nn.LayerNorm(d) for d in config.hidden)
        self.lifs = nn.ModuleList(snn.Leaky(beta=0.9, learn_beta=True, spike_grad=surrogate.fast_sigmoid(slope=25), init_hidden=False) for _ in config.hidden)
        self.drop = nn.Dropout(config.dropout)
        self.readout = nn.Linear(config.hidden[-1], classes)

    def forward(self, x):
        code = self.encoder(x)
        membranes = [torch.zeros(x.shape[0], layer.out_features, device=x.device) for layer in self.linears]
        outputs = []
        for spikes in code:
            for i, (linear, norm, lif) in enumerate(zip(self.linears, self.norms, self.lifs)):
                spikes, membranes[i] = lif(norm(linear(spikes)), membranes[i])
                spikes = self.drop(spikes)
            outputs.append(self.readout(spikes))
        return torch.stack(outputs).mean(0)


class Fusion(nn.Module):
    def __init__(self, branches, classes, alpha):
        super().__init__()
        self.branches = nn.ModuleDict(branches)
        self.alpha = alpha
        if len(branches) == 1:
            return
        if alpha > 0:
            self.weights = nn.Parameter(torch.zeros(len(branches)))
        if alpha < 1:
            self.meta = nn.Sequential(nn.Linear(classes*len(branches), 64), nn.GELU(), nn.Linear(64, classes))

    def forward(self, x):
        predictions = [branch(x) for branch in self.branches.values()]
        if len(predictions) == 1:
            return predictions[0]
        if self.alpha == 0:
            return self.meta(torch.cat(predictions, 1))
        weighted = (torch.stack(predictions) * self.weights.softmax(0)[:, None, None]).sum(0)
        if self.alpha == 1:
            return weighted
        return self.alpha*weighted+(1-self.alpha)*self.meta(torch.cat(predictions, 1))


class ANN(nn.Module):
    def __init__(self, features, classes, widths, dropout):
        super().__init__()
        layers = []
        for width in widths:
            layers.extend([nn.Linear(features, width), nn.LayerNorm(width), nn.GELU(), nn.Dropout(dropout)])
            features = width
        self.layers = nn.Sequential(*layers, nn.Linear(features, classes))

    def forward(self, x):
        return self.layers(x)


class CNN(nn.Module):
    def __init__(self, features, classes, config):
        super().__init__()
        self.layers = nn.Sequential(nn.Conv1d(1, 32, 3, padding=1), nn.GELU(),
                                    nn.Conv1d(32, 64, 3, padding=1), nn.GELU(),
                                    nn.AdaptiveAvgPool1d(4), nn.Flatten(), nn.Linear(256, classes))

    def forward(self, x):
        return self.layers(x[:, None])


class EncodedANN(nn.Module):
    """Same deterministic spike input, feed-forward processing over flattened time.

    A mechanistic control, not an external state-of-the-art model. Width is chosen
    using parameter counts alone, with no label or validation access.
    """
    def __init__(self, features, classes, kind, config):
        super().__init__()
        self.encoder = FixedEncoder(kind, config.steps, config.populations, config.scaler == "quantile")
        d = features * config.steps * (config.populations if kind == "population" else 1)
        # Analytical count avoids constructing a randomly initialized SNN.
        dims = [features*(config.populations if kind == "population" else 1), *config.hidden]
        target = sum((a+1)*b+2*b+1 for a,b in zip(dims,dims[1:])) + (dims[-1]+1)*classes
        def count(w):
            return (d+1)*w+2*w+(w+1)*w+2*w+(w+1)*classes
        width = min(range(4,1025), key=lambda w: abs(count(w)-target))
        self.network = ANN(d, classes, (width,width), config.dropout)

    def forward(self, x):
        return self.network(self.encoder(x).permute(1,0,2).flatten(1))


def build(name, features, classes, config):
    if name == "encoded_ann":
        return Fusion({k: EncodedANN(features, classes, k, config) for k in config.branches}, classes, config.alpha)
    if name == "esnn":
        return Fusion({k: SpikeBranch(features, classes, k, config) for k in config.branches}, classes, config.alpha)
    if name == "ann_ensemble":
        return Fusion({k: ANN(features, classes, config.hidden, config.dropout) for k in config.branches}, classes, config.alpha)
    if name == "ann":
        # Select width from parameter counts, not validation/test performance.
        target = sum(p.numel() for p in build("esnn", features, classes, config).parameters())
        def number(width):
            return (features+1)*width + 2*width + (width+1)*width + 2*width + (width+1)*classes
        width = min(range(16, 1025), key=lambda w: abs(number(w)-target))
        return ANN(features, classes, (width, width), config.dropout)
    if name == "cnn":
        return CNN(features, classes, config)
    raise ValueError(name)
