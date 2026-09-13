import subprocess, time, urllib.request, json, websocket, os

def test_profile(p, port):
    pid = p['id']
    data_dir = os.path.join(os.environ['TEMP'], f'mun_test_prof_{pid}')
    os.makedirs(data_dir, exist_ok=True)
    for lock in ['SingletonLock', 'SingletonCookie', 'SingletonSocket', 'lockfile']:
        try: os.remove(os.path.join(data_dir, lock))
        except: pass
        
    chrome = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    cmd = [
        chrome,
        f'--remote-debugging-port={port}',
        '--remote-allow-origins=*',
        f'--user-data-dir={data_dir}',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-blink-features=AutomationControlled',
        '--window-size=1920,1080',
        f'--user-agent={p["profile_user_agent"]}',
        'about:blank'
    ]
    proc = subprocess.Popen(cmd)
    time.sleep(2)
    
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/json') as r:
        pages = json.loads(r.read())
    page = next(item for item in pages if item.get('type') == 'page')
    ws = websocket.create_connection(page['webSocketDebuggerUrl'])
    
    ua = p['profile_user_agent']
    ws.send(json.dumps({
        'id': 1,
        'method': 'Emulation.setUserAgentOverride',
        'params': {
            'userAgent': ua,
            'acceptLanguage': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
            'platform': 'Win32'
        }
    }))
    
    p_id = p['id']
    r_shift = ((p_id * 17 + 7) % 7) - 3
    g_shift = ((p_id * 31 + 13) % 7) - 3
    b_shift = ((p_id * 47 + 19) % 7) - 3
    if r_shift == 0 and g_shift == 0 and b_shift == 0:
        r_shift, g_shift, b_shift = 1, -1, 1
    renderer = p['gpu_renderer']
    vendor = p['gpu_vendor']
    
    stealth_js = f"""
    (() => {{
        const origGetImg = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {{
            const imgData = origGetImg.apply(this, arguments);
            for (let i = 0; i < imgData.data.length; i += 4) {{
                imgData.data[i] = Math.max(0, Math.min(255, imgData.data[i] + ({r_shift})));
                imgData.data[i+1] = Math.max(0, Math.min(255, imgData.data[i+1] + ({g_shift})));
                imgData.data[i+2] = Math.max(0, Math.min(255, imgData.data[i+2] + ({b_shift})));
            }}
            return imgData;
        }};
        
        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function() {{
            const ctx = this.getContext('2d');
            if (ctx && this.width > 0 && this.height > 0) {{
                try {{
                    const imgData = origGetImg.call(ctx, 0, 0, Math.min(10, this.width), Math.min(10, this.height));
                    imgData.data[0] = Math.max(0, Math.min(255, imgData.data[0] + ({r_shift})));
                    ctx.putImageData(imgData, 0, 0);
                }} catch(e) {{}}
            }}
            return origToDataURL.apply(this, arguments);
        }};
        
        const getParam = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(param) {{
            if (param === 37445) return '{vendor}';
            if (param === 37446) return '{renderer}';
            return getParam.apply(this, arguments);
        }};
        if (window.WebGL2RenderingContext) {{
            const getParam2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(param) {{
                if (param === 37445) return '{vendor}';
                if (param === 37446) return '{renderer}';
                return getParam2.apply(this, arguments);
            }};
        }}
    }})();
    """
    
    ws.send(json.dumps({
        'id': 2,
        'method': 'Page.addScriptToEvaluateOnNewDocument',
        'params': {'source': stealth_js}
    }))
    
    ws.send(json.dumps({'id': 3, 'method': 'Page.navigate', 'params': {'url': 'https://iphey.com'}}))
    print(f"Profile #{p_id} ({renderer[:35]}...) navigating to iphey.com...")
    
    time.sleep(7)
    
    code = """
    JSON.stringify({
        title: document.querySelector('.main-title, h1, .title')?.innerText || '',
        hardware: Array.from(document.querySelectorAll('*')).find(el => el.innerText === 'HARDWARE')?.parentElement?.innerText || '',
        software: Array.from(document.querySelectorAll('*')).find(el => el.innerText === 'SOFTWARE')?.parentElement?.innerText || '',
        webgl_renderer: (() => {
            const c = document.createElement('canvas');
            const gl = c.getContext('webgl');
            return gl ? gl.getParameter(37446) : '';
        })()
    })
    """
    ws.send(json.dumps({'id': 4, 'method': 'Runtime.evaluate', 'params': {'expression': code, 'returnByValue': True}}))
    while True:
        res = json.loads(ws.recv())
        if res.get('id') == 4:
            break
    data = json.loads(res['result']['result']['value'])
    print(f"RESULT for Profile #{p_id}:", json.dumps(data, ensure_ascii=False))
    ws.close()
    proc.terminate()

if __name__ == '__main__':
    with open(r'D:\Workspace\Python\QHTDautomation\MunAutomationDesktop\browser_profiles.json', 'r', encoding='utf-8') as f:
        profs = json.load(f)

    test_profile(profs[0], 9222)
    time.sleep(2)
    test_profile(profs[1], 9223)
