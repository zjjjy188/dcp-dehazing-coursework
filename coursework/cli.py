import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from .core import Config, dehaze


def load(path):
    with Image.open(path) as image:
        return np.asarray(ImageOps.exif_transpose(image).convert('RGB'), dtype=np.float64) / 255


def save(path, image):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.round(np.clip(image, 0, 1) * 255).astype('uint8')).save(path)


def main():
    parser = argparse.ArgumentParser(description='暗通道图像去雾，支持中文路径和批处理')
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, default=Path('outputs'))
    parser.add_argument('--mode', choices=['fast', 'improved'], default='improved')
    args = parser.parse_args()
    import json
    cfg = Config()
    config_path = Path(__file__).resolve().parents[1] / 'results' / 'selected_config.json'
    if args.mode == 'improved':
        if not config_path.exists():
            parser.error('尚未选定改进参数，请先执行 python -m coursework.experiment')
        cfg = Config(**json.loads(config_path.read_text(encoding='utf-8')))
    paths = [args.input] if args.input.is_file() else sorted(p for p in args.input.iterdir() if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.bmp', '.webp'})
    if not paths:
        parser.error('没有找到可处理的图像')
    for path in paths:
        output, extra = dehaze(load(path), cfg, details=True)
        save(args.output / f'{path.stem}_{args.mode}.png', output)
        save(args.output / f'{path.stem}_transmission.png', extra['transmission'])
        print(f'处理完成：{path.name}')


if __name__ == '__main__':
    main()
