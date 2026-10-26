"""A fixed development matrix. Old v2 test exposure is explicitly retained."""
from pathlib import Path
import datetime as dt
import shutil
import sys
import time
import zipfile
from .config import Config
from .kaggle import run_command
from .provenance import read_json, write_json, file_hash

EXPERIMENTS = ('group_ce', 'group_weighted')


def compact_archive(root):
    root = Path(root)
    dest = root/'IDS2018_REVIEW_LIGHT.zip'
    # Explicit allowlist: never include model checkpoints, probabilities, data,
    # input CSVs, or other zip files. Full Notebook Output is for resuming only.
    candidates = [p for name in ('experiments','reports') for p in (root/name).rglob('*')
                  if p.is_file() and p.suffix in ('.json','.md','.tex','.bib') and p.name != 'resume.json']
    candidates += [p for p in root.glob('*') if p.is_file() and p.suffix in ('.json','.txt','.md')]
    with zipfile.ZipFile(dest.with_suffix('.tmp'), 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(set(candidates)):
            z.write(p, p.relative_to(root))
    dest.with_suffix('.tmp').replace(dest)
    return dest


def run_suite(root, data, timestamp_format, device='cuda', hours=9., bundle_id=None):
    root = Path(root)
    repo = root/'code'
    state_path = root/'v3-state.json'
    if state_path.exists() and read_json(state_path)['bundle_id'] != bundle_id:
        raise ValueError('This directory belongs to another source bundle')
    state = {'bundle_id': bundle_id, 'status': 'running', 'trained': [], 'evaluated': [],
             'expected_runs': 24, 'experiments': list(EXPERIMENTS),
             'evidence_status': 'development_after_v2_test_inspection; not independent confirmation'}
    start = time.monotonic()
    def save():
        state['updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
        write_json(state_path,state)
    def expired():
        return (time.monotonic()-start)/3600 >= hours
    try:
        save()
        # Refuse dataset changes on resume; training arrays alone are not enough.
        manifests = list((root/'experiments').glob('*/manifest.json'))
        if manifests:
            for f in read_json(manifests[0])['dataset']['files']:
                if file_hash(Path(data)/f['file']) != f['sha256']:
                    raise ValueError('Attached dataset changed since preparation')
        for label in EXPERIMENTS:
            exp = root/'experiments'/label
            cfg = Config.read(repo/'configs'/f'{label}.json')
            if not (exp/'manifest.json').exists():
                if expired():
                    state['status']='paused'; return state
                if shutil.disk_usage(root).free < 6*1024**3:
                    raise RuntimeError('Preparation needs at least 6 GiB free output space. Preserve prior Output before continuing in a fresh session.')
                run_command(repo,'prepare','--data',data,'--config',repo/'configs'/f'{label}.json',
                            '--out',exp,'--timestamp-format',timestamp_format)
            from .pipeline import validated
            manifest, prepared = validated(exp)
            if prepared.dictionary() != cfg.dictionary():
                raise ValueError('Prepared config differs from declared suite')
            for seed in cfg.seeds:
                for model in cfg.models:
                    if expired():
                        state['status']='paused'; return state
                    run_command(repo,'train','--experiment',exp,'--models',model,'--seeds',seed,
                                '--device', 'cpu' if model in ('rf','xgb','catboost') else device)
                    state['trained'].append(f'{label}/{model}-{seed}'); save()
        # No test inference occurs until all declared models in both arms train.
        for label in EXPERIMENTS:
            exp = root/'experiments'/label
            cfg = Config.read(repo/'configs'/f'{label}.json')
            for seed in cfg.seeds:
                for model in cfg.models:
                    if expired():
                        state['status']='paused'; return state
                    run_command(repo,'evaluate','--experiment',exp,'--models',model,'--seeds',seed,
                                '--device','cpu' if model in ('rf','xgb','catboost') else device)
                    state['evaluated'].append(f'{label}/{model}-{seed}'); save()
            run_command(repo,'export','--experiment',exp,'--out',root/'reports'/label,'--draft')
        state['status']='completed_development_matrix'
        return state
    except BaseException as exc:
        state['status']='interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed'
        state['error']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        save()
        (root/'STATUS_TR.md').write_text('Durum: '+state['status']+'\n\n'
            'Bu çalışma geliştirme deneyidir. Önceki v2 test sonuçları incelendiği için yeni bağımsız doğrulama sayılmaz. '
            'Yalnız IDS2018_REVIEW_LIGHT.zip inceleme için indirilir. Kaldığı yerden devam etmek için tüm Notebook Output saklanır.\n')
        print('İnceleme dosyası:',compact_archive(root),flush=True)
