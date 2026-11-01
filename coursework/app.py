"""本地 Gradio 演示，不向公网分享图像。"""
from dataclasses import replace
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image
import gradio as gr
from .core import Config, dehaze

ROOT = Path(__file__).resolve().parents[1]
CSS = '''
.gradio-container {max-width: 1440px !important; background: #FFFFFF; font-family: "Helvetica Neue", "Microsoft YaHei", sans-serif;}
.gradio-container h1 {font-size: 32px; text-align: left; color: #111111;}
.gradio-container .block {border-radius: 0; border: 1px solid #dddddf; box-shadow: none;}
button.primary {background: #002FA7 !important; color: white !important; border-radius: 0 !important;}
'''


def process(image, strength):
    if image is None:
        raise gr.Error('请先上传图像')
    pil = Image.fromarray(image).convert('RGB')
    pil.thumbnail((1280,1280),Image.Resampling.LANCZOS)
    image = np.asarray(pil,dtype=np.float64)/255
    config_path=ROOT/'results'/'selected_config.json'
    if not config_path.exists():
        raise gr.Error('请先运行实验，生成验证集选定的改进参数')
    cfg=Config(**json.loads(config_path.read_text(encoding='utf-8')))
    cfg=replace(cfg,omega=float(strength))
    start=time.perf_counter()
    original=dehaze(image,Config(omega=float(strength)))
    improved,detail=dehaze(image,cfg,details=True)
    elapsed=time.perf_counter()-start
    def uint8(x): return np.round(x*255).astype('uint8')
    return uint8(original),uint8(improved),uint8(detail['transmission']),f'处理尺寸 {image.shape[1]} × {image.shape[0]}，两种方法合计用时 {elapsed:.3f} 秒。原版效果使用已验证等价的加速实现。'


def build_app():
    with gr.Blocks(title='暗通道图像去雾') as app:
        gr.Markdown('# 暗通道图像去雾\n上传有雾图像，比较原版效果与验证集选定的改进效果。')
        with gr.Row():
            source=gr.Image(label='输入图像',type='numpy',image_mode='RGB')
            with gr.Column():
                strength=gr.Slider(.5,1,value=.95,step=.01,label='去雾强度')
                run=gr.Button('开始去雾',variant='primary')
                status=gr.Textbox(label='处理状态',interactive=False)
                gr.Markdown('图像在本机处理。大图会缩放至最长边 1280 像素。透射率图中较暗的区域通常需要更强的雾霾补偿。')
        with gr.Row():
            original=gr.Image(label='原版效果',interactive=False)
            improved=gr.Image(label='改进版效果',interactive=False)
            transmission=gr.Image(label='改进版透射率',interactive=False)
        gr.Examples(examples=[[str(ROOT/'images'/'street.jpg')],[str(ROOT/'images'/'forest.jpg')]],inputs=source,label='原项目示例')
        run.click(process,[source,strength],[original,improved,transmission,status])
    return app


if __name__=='__main__':
    build_app().launch(server_name='127.0.0.1',share=False,css=CSS)
