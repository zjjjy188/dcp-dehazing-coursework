"""固定数据划分、验证集选参、独立测试、消融与计时。"""
from dataclasses import asdict, replace
from pathlib import Path
import csv
import hashlib
import json
import platform
import sys
import time
import urllib.request
import numpy as np
from PIL import Image
from .core import Config, dehaze, dark_channel, guided_filter
from .cli import load, save
from .metrics import psnr, ssim

ROOT = Path(__file__).resolve().parents[1]
IDS = ['100007','100039','100099','10081','101027','101084','102062','103006','103029','103078','104010','104055','105027','106005','106047','107014','107045','107072','108004','108036','108069','109055','112056','112090','117025','118015','118031','118072']
CONDITIONS = [('light', .6, [.85,.88,.92]), ('medium', 1.0, [.9,.9,.9]), ('heavy', 1.5, [.9,.93,.97])]


def baseline(image):
    # 上游文件保持原样；仅统一输入输出范围，并裁剪浮点结果后计算指标。
    import dehazing
    original = image * 255
    dark = dehazing.dark_channel(original, 15)
    atmosphere = dehazing.atmospheric_light(original, dark)
    transmission = dehazing.transmission(original, atmosphere, 15)
    transmission = dehazing.refine_transmission(original, transmission, 40, .001)
    return np.clip(dehazing.recover_radiance(original, atmosphere, transmission) / 255, 0, 1)


def prepare():
    folder = ROOT / 'data' / 'clean'
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for index, name in enumerate(IDS):
        path = folder / f'{name}.jpg'
        url = f'https://raw.githubusercontent.com/BIDS/BSDS500/a04b7c6c3a9f0ace74bf205c72a43d32e1c72722/BSDS500/data/images/test/{name}.jpg'
        if not path.exists():
            with urllib.request.urlopen(url, timeout=60) as response:
                path.write_bytes(response.read())
        records.append({'id': name, 'split': 'validation' if index < 16 else 'test', 'url': url, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        print(f'数据已准备 {index + 1}/{len(IDS)}', flush=True)
    (ROOT / 'data' / 'manifest.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    return records


def examples(records, split):
    for record in records:
        if record['split'] != split:
            continue
        with Image.open(ROOT / 'data' / 'clean' / f"{record['id']}.jpg") as image:
            image = image.convert('RGB')
            image.thumbnail((320,320), Image.Resampling.LANCZOS)
            clean = np.asarray(image, dtype=np.float64) / 255
        h, w = clean.shape[:2]
        y, x = np.mgrid[0:h,0:w].astype(np.float64)
        # 人工构造的平滑深度代理，不是真实深度，不能代表标准去雾数据集。
        depth = .35 + .9 * (1 - y / max(h-1,1)) + .15 * np.sin(2*np.pi*x/max(w-1,1))**2
        for condition, beta, atmosphere in CONDITIONS:
            transmission = np.exp(-beta * depth)[...,None]
            hazy = clean * transmission + np.array(atmosphere) * (1 - transmission)
            # 模拟实际 8 位输入，真值保留原干净图像。
            hazy = np.round(hazy * 255) / 255
            yield record['id'], condition, clean, hazy


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def check_equivalence():
    import dehazing
    import guidedfilter
    rng = np.random.default_rng(42)
    image = rng.uniform(.1,.9,(91,103,3))
    assert np.allclose(dark_channel(image), dehazing.dark_channel(image,15), atol=1e-12)
    src = rng.uniform(.1,.9,(91,103))
    fast = guided_filter(image, src,40,.001)
    slow = guidedfilter.filter(image,src,40,.001)
    err = float(np.max(np.abs(fast-slow)))
    assert err < 1e-8, err
    # 与上游 0..255 完整流水线对齐，包含正则项缩放。
    error = float(np.max(np.abs(dehaze(image)-baseline(image))))
    assert error < 1e-6, error
    for shape in [(1,1,3),(3,7,3),(81,81,3)]:
        out = dehaze(np.zeros(shape))
        assert np.isfinite(out).all() and out.min() >= 0 and out.max() <= 1
    try:
        dehaze(np.full((3,3,3),np.nan))
    except ValueError:
        pass
    else:
        raise AssertionError('必须拒绝非有限值')
    return {'guided_filter_max_error': err, 'pipeline_max_error': error, 'tiny_and_black_inputs': 'passed'}


def main():
    result_dir = ROOT / 'results'
    result_dir.mkdir(exist_ok=True)
    checks = check_equivalence()
    print(f'原版等价性与边界检查通过 {checks}', flush=True)
    records = prepare()
    validation = list(examples(records,'validation'))
    # 只在验证图像上选择参数；测试集不参与选择。
    candidates = [('fast',Config())]
    for eps in [1e-4,1e-3,1e-2]:
        for robust in [False,True]:
            for protection in [0,.2,.4]:
                candidates.append((f'eps{eps}_robust{robust}_protect{protection}',Config(eps=eps,robust_airlight=robust,bright_protection=protection)))
    scores = []
    for name,cfg in candidates:
        values = [psnr(clean,dehaze(hazy,cfg)) for _,_,clean,hazy in validation]
        scores.append({'candidate':name,'mean_psnr':float(np.mean(values)),**asdict(cfg)})
    write_csv(result_dir / 'validation_search.csv',scores)
    selected_index = int(np.argmax([s['mean_psnr'] for s in scores]))
    selected_name, selected = candidates[selected_index]
    (result_dir / 'selected_config.json').write_text(json.dumps(asdict(selected),indent=2),encoding='utf-8')
    print(f'验证集选择 {selected_name}：{scores[selected_index]["mean_psnr"]:.3f} dB',flush=True)
    methods = {
        'hazy': lambda image:image,
        'original':baseline,
        'fast':lambda image:dehaze(image),
        'regularized':lambda image:dehaze(image,Config(eps=selected.eps)),
        'airlight':lambda image:dehaze(image,Config(eps=selected.eps,robust_airlight=True)),
        'bright_protection':lambda image:dehaze(image,replace(selected,bright_protection=.2)),
        'improved':lambda image:dehaze(image,selected),
    }
    rows=[]
    for i,(name,condition,clean,hazy) in enumerate(examples(records,'test')):
        for method,function in methods.items():
            start=time.perf_counter()
            output=function(hazy)
            elapsed=time.perf_counter()-start
            rows.append({'image':name,'condition':condition,'method':method,'psnr':psnr(clean,output),'ssim':ssim(clean,output),'seconds':elapsed})
            if condition == 'medium':
                save(result_dir / 'examples' / name / f'{method}.png',output)
        if condition == 'medium':
            save(result_dir / 'examples' / name / 'clean.png',clean)
        print(f'测试样本完成 {i+1}/36：{name} {condition}',flush=True)
    write_csv(result_dir / 'metrics.csv',rows)
    summary = {}
    for method in methods:
        group=[row for row in rows if row['method']==method]
        summary[method]={key:float(np.mean([r[key] for r in group])) for key in ['psnr','ssim','seconds']}
    # 相同样本、相同输出精度；预热后交替计时三次，中位数降低偶然抖动。
    benchmark_image=validation[0][3]
    baseline(benchmark_image); dehaze(benchmark_image)
    timings={'original':[],'fast':[]}
    for _ in range(3):
        for name,function in [('original',baseline),('fast',dehaze)]:
            start=time.perf_counter(); function(benchmark_image)
            timings[name].append(time.perf_counter()-start)
    medians={key:float(np.median(value)) for key,value in timings.items()}
    real=[]
    for path in sorted((ROOT/'images').glob('*.jpg')):
        if path.stem not in {'street','forest'}:
            continue
        image=load(path)
        output,detail=dehaze(image,selected,details=True)
        save(result_dir/'real'/f'{path.stem}_input.png',image)
        save(result_dir/'real'/f'{path.stem}_improved.png',output)
        save(result_dir/'real'/f'{path.stem}_original.png',baseline(image))
        save(result_dir/'real'/f'{path.stem}_transmission.png',detail['transmission'])
        real.append(path.name)
    report={'selected_candidate':selected_name,'validation_count':len(validation),'test_count':36,'summary':summary,'checks':checks,'benchmark':{'shape':list(benchmark_image.shape),'repeats':3,'raw_seconds':timings,'median_seconds':medians,'speedup':medians['original']/medians['fast']},'environment':{'python':sys.version,'platform':platform.platform(),'numpy':np.__version__},'real_examples':real,'limitations':['28 张 BSDS500 图像按文件名选择的教学子集，不代表完整标准基准','合成雾使用人工深度代理，不是真实深度或真实成对雾图','真实雾图无真值，只进行定性观察','所有实现均使用 CPU，GPU 未参与计时','原版结果统一裁剪到 0..1，避免原 main.py 的 uint8 越界回绕','先导试验的全部 16 张图像已纳入开发集；最终 12 张测试图像为全新保留集']}
    (result_dir/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    main()
