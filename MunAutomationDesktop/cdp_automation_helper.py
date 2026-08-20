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
    """Click tọa độ thật của nút / link / thẻ có text tương ứng qua CDP"""
    kw_json = json.dumps([k.lower() for k in keywords])
    res = await tab.evaluate(f"""
    (() => {{
        const kws = {kw_json};
        const allElements = Array.from(document.querySelectorAll("button, input[type='submit'], input[type='button'], a, span, div.fui-Button, [role='button']"));
        const targetBtn = allElements.find(b => {{
            const t = (b.innerText || b.value || b.textContent || "").trim().toLowerCase();
            return kws.some(k => t.includes(k)) || b.id === "idSIButton9" || b.id === "idBtn_Accept" || b.id === "idA_PWD_SwitchToPassword";
        }});
        if (targetBtn) {{
            targetBtn.focus();
            targetBtn.click(); // Click native DOM trước
            const rect = targetBtn.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {{
                return JSON.stringify({{ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, text: targetBtn.innerText }});
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
