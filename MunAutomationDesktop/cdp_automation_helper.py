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

async def cdp_click_btn_by_text(tab, keywords=["next", "sign in", "yes", "ok", "got it", "continue"]):
    """Click tọa độ thật của nút có text tương ứng qua CDP"""
    kw_json = json.dumps([k.lower() for k in keywords])
    res = await tab.evaluate(f"""
    (() => {{
        const kws = {kw_json};
        const allBtns = Array.from(document.querySelectorAll("button, input[type='submit'], input[type='button']"));
        const targetBtn = allBtns.find(b => {{
            const t = (b.innerText || b.value || "").trim().toLowerCase();
            return kws.includes(t) || b.id === "idSIButton9" || b.id === "idBtn_Accept";
        }});
        if (targetBtn) {{
            const rect = targetBtn.getBoundingClientRect();
            return JSON.stringify({{ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, text: targetBtn.innerText }});
        }}
        return null;
    }})()
    """)
    if res:
        box = json.loads(res)
        await tab.send(cdp_in.dispatch_mouse_event(type_="mousePressed", x=box['x'], y=box['y'], button=cdp_in.MouseButton.LEFT, click_count=1))
        await tab.send(cdp_in.dispatch_mouse_event(type_="mouseReleased", x=box['x'], y=box['y'], button=cdp_in.MouseButton.LEFT, click_count=1))
        return True
    return False
