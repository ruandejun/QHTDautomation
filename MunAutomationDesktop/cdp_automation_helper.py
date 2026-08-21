import os, sys, asyncio, logging, json, requests, random, time
import nodriver.cdp.input_ as cdp_in

async def cdp_type_code_6digits(tab, code_str: str):
    """Điền mã OTP 6 số vào giao diện ô đơn hoặc 6 ô rời (#codeEntry-0..5) của Microsoft"""
    code_str = str(code_str).strip()
    if len(code_str) != 6:
        return False
        
    res = await tab.evaluate("""
    (() => {
        const singleInput = document.querySelector("#iOttText, input[name='iOttText'], input[name='otc'], input[id*='OTC'], input[type='tel']");
        if (singleInput) {
            return JSON.stringify({ mode: "single", selector: "#iOttText" });
        }
        const box0 = document.querySelector("#codeEntry-0");
        if (box0) {
            return JSON.stringify({ mode: "boxes" });
        }
        return null;
    })()
    """)
    if not res:
        return False
        
    info = json.loads(res)
    if info.get("mode") == "single":
        return await cdp_type_text(tab, "#iOttText, input[id='iOttText'], input[name='iOttText'], input[name='otc'], input[id*='OTC'], input[type='tel']", code_str)
    else:
        # Gõ lần lượt vào 6 ô codeEntry-0 tới codeEntry-5
        for i in range(6):
            digit = code_str[i]
            await tab.evaluate(f"""
            (() => {{
                const el = document.querySelector("#codeEntry-{i}");
                if (el) {{
                    el.focus();
                    el.value = "{digit}";
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }})()
            """)
            await asyncio.sleep(0.05)
        return True

async def cdp_type_text(tab, selector, text):
    """Click trực tiếp vào tọa độ thật của phần tử, xóa sạch text cũ (Ctrl+A -> Backspace) và gõ từng phím qua CDP"""
    res = await tab.evaluate(f"""
    (() => {{
        const el = document.querySelector("{selector}");
        if (el) {{
            el.focus();
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
        await asyncio.sleep(0.2)
        
        # Xóa sạch nội dung cũ trước khi gõ bằng Ctrl+A -> Backspace
        await tab.send(cdp_in.dispatch_key_event(type_="keyDown", modifiers=2, text="a", key="a", windows_virtual_key_code=65))
        await tab.send(cdp_in.dispatch_key_event(type_="keyUp", modifiers=2, text="a", key="a", windows_virtual_key_code=65))
        await asyncio.sleep(0.05)
        await tab.send(cdp_in.dispatch_key_event(type_="keyDown", key="Backspace", windows_virtual_key_code=8))
        await tab.send(cdp_in.dispatch_key_event(type_="keyUp", key="Backspace", windows_virtual_key_code=8))
        await asyncio.sleep(0.1)

        # Xóa bằng JS DOM value để chắc chắn 100% rỗng
        await tab.evaluate(f"""
        (() => {{
            const el = document.querySelector("{selector}");
            if (el) {{
                el.value = "";
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        }})()
        """)
        await asyncio.sleep(0.1)

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
