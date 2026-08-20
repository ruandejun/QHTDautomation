import os, sys, asyncio, logging, json, requests, random, time
import nodriver.cdp.input_ as cdp_in

async def cdp_type_text(tab, selector, text):
    """Click trực tiếp vào tọa độ thật của phần tử và gõ từng phím qua CDP"""
    res = await tab.evaluate(f"""
    (() => {{
        const el = document.querySelector("{selector}");
        if (el) {{
            const rect = el.getBoundingClientRect();
            return JSON.stringify({{ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 }});
        }}
        return null;
    }})()
    """)
    if res:
        box = json.loads(res)
        await tab.send(cdp_in.dispatch_mouse_event(type_="mousePressed", x=box['x'], y=box['y'], button=cdp_in.MouseButton.LEFT, click_count=1))
        await tab.send(cdp_in.dispatch_mouse_event(type_="mouseReleased", x=box['x'], y=box['y'], button=cdp_in.MouseButton.LEFT, click_count=1))
        await asyncio.sleep(0.3)
        for char in text:
            await tab.send(cdp_in.dispatch_key_event(type_="keyDown", text=char, key=char))
            await tab.send(cdp_in.dispatch_key_event(type_="keyUp", key=char))
            await asyncio.sleep(0.02)
        return True
    return False

async def cdp_click_btn_by_text(tab, keywords=["next", "sign in", "yes", "ok", "got it", "continue", "use your password", "other ways to sign in"]):
    """Click tọa độ thật của phần tử lá (leaf node) hoặc nút có text tương ứng qua CDP"""
    kw_json = json.dumps([k.lower() for k in keywords])
    res = await tab.evaluate(f"""
    (() => {{
        const kws = {kw_json};
        const allElements = Array.from(document.querySelectorAll("*"));
        
        // 1. Ưu tiên tìm Leaf Node có text khớp chính xác 100% với keyword
        let target = allElements.find(e => {{
            const t = (e.innerText || e.textContent || e.value || "").trim().toLowerCase();
            if (!kws.includes(t)) return false;
            // Đảm bảo là leaf node (không có con nào cũng có text đó)
            return !Array.from(e.children).some(c => kws.includes((c.innerText || c.textContent || "").trim().toLowerCase()));
        }});
        
        // 2. Nếu không có leaf node khớp chính xác, tìm theo includes hoặc selector chuẩn
        if (!target) {{
            target = allElements.find(b => {{
                const t = (b.innerText || b.value || b.textContent || "").trim().toLowerCase();
                return kws.some(k => t === k || (k.length > 5 && t.includes(k))) || b.id === "idSIButton9" || b.id === "idBtn_Accept" || b.id === "idA_PWD_SwitchToPassword";
            }});
        }}
        
        if (target) {{
            target.scrollIntoView();
            target.focus();
            try {{ target.click(); }} catch(e) {{}}
            const rect = target.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {{
                return JSON.stringify({{ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, text: target.innerText || target.textContent }});
            }}
            return JSON.stringify({{ x: -1, y: -1 }});
        }}
        return null;
    }})()
    """)
    if res:
        box = json.loads(res)
        if box.get('x', -1) > 0:
            await tab.send(cdp_in.dispatch_mouse_event(type_="mousePressed", x=box['x'], y=box['y'], button=cdp_in.MouseButton.LEFT, click_count=1))
            await tab.send(cdp_in.dispatch_mouse_event(type_="mouseReleased", x=box['x'], y=box['y'], button=cdp_in.MouseButton.LEFT, click_count=1))
        return True
    return False
