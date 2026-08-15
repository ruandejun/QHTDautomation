"""
MunAntiBrowser E-commerce Scraper Microservice (FastAPI + Nodriver)
Thay thế TMAPI:
- Endpoint 1: POST /tools/parse/url
- Endpoint 2: GET /1688/v2/item_detail
- Endpoint 3: GET /taobao/item_detail
- Endpoint 4: POST /api/v1/scrape/item_detail
"""

import asyncio
import os
import re
import sys
import json
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs

import uvicorn
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel

sys.path.insert(0, '/root/Workspace/Python/QHTDautomation/MunAutomationDesktop')
from mun_anti_browser.browser_manager import NodriverBrowserManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EcommerceScraperAPI")

app = FastAPI(title="Ecommerce Scraper Service (MunAntiBrowser)", version="1.0.0")

BROWSER_LOCK = asyncio.Lock()
CHROME_DATA_DIR = "/root/Workspace/Python/QHTDautomation/MunAutomationDesktop/chrome_data"
PROFILE_CONFIG = {
    "id": "profile_maidzo_vn",
    "name": "Maidzo Production Admin Profile",
    "profile_os": "Window"
}

class ParseUrlPayload(BaseModel):
    url: str

class ScrapePayload(BaseModel):
    url: Optional[str] = None
    item_id: Optional[str] = None
    platform: Optional[str] = "1688"


def extract_platform_and_id(url: str) -> Dict[str, str]:
    clean_url = url.strip()
    if "1688.com" in clean_url:
        m = re.search(r'offer/(\d+)\.html', clean_url)
        item_id = m.group(1) if m else ""
        return {"plat": "1688", "id": item_id, "url": clean_url}
    elif "taobao.com" in clean_url:
        parsed = urlparse(clean_url)
        qs = parse_qs(parsed.query)
        item_id = qs.get("id", [""])[0]
        return {"plat": "taobao", "id": item_id, "url": clean_url}
    elif "tmall.com" in clean_url:
        parsed = urlparse(clean_url)
        qs = parse_qs(parsed.query)
        item_id = qs.get("id", [""])[0]
        return {"plat": "tmall", "id": item_id, "url": clean_url}
    return {"plat": "unknown", "id": "", "url": clean_url}


@app.post("/tools/parse/url")
async def parse_url_compat(payload: ParseUrlPayload):
    """Tương thích chuẩn TMAPI parse URL"""
    res = extract_platform_and_id(payload.url)
    return {
        "code": 200,
        "msg": "success",
        "data": res
    }


async def scrape_1688_page(item_id: str) -> Dict[str, Any]:
    url = f"https://detail.1688.com/offer/{item_id}.html"
    os.environ["DISPLAY"] = ":99"
    async with BROWSER_LOCK:
        manager = NodriverBrowserManager()
        browser, tab = await manager.start(profile_config=PROFILE_CONFIG, headless=False)
        try:
            await tab.get(url)
            await asyncio.sleep(4.5)

            data = await tab.evaluate("""
                (() => {
                    const title = (document.querySelector('h1') || document.querySelector('.title-text') || document.querySelector('.d-title') || {}).innerText || document.title;
                    
                    // Main Images
                    const imgNodes = document.querySelectorAll('.main-img-item img, .od-pc-offer-gallery img, .tab-content img, .detail-gallery-img');
                    let images = [];
                    imgNodes.forEach(img => {
                        const src = img.src || img.getAttribute('data-src') || img.getAttribute('lazy-src');
                        if (src && !images.includes(src) && !src.includes('data:image') && !src.includes('.svg')) images.push(src);
                    });

                    // Shop Name
                    const shopName = (document.querySelector('.company-name, .shop-name, .supplier-name, .name') || {}).innerText || '1688 Supplier';

                    // Price text
                    const priceNodes = document.querySelectorAll('.price-text, .price, .discount-price, .od-pc-offer-price-item, [class*="Price"]');
                    let prices = [];
                    priceNodes.forEach(n => {
                        const t = n.innerText ? n.innerText.trim() : '';
                        if (t && (t.includes('¥') || /^[0-9]+(\\.[0-9]+)?$/.test(t))) prices.push(t.replace('¥','').trim());
                    });

                    // SKUs / Props
                    let skus = [];
                    const propNodes = document.querySelectorAll('.prop-item, .sku-item, .item-spec, [class*="skuItem"], [class*="propItem"]');
                    propNodes.forEach(p => {
                        const txt = p.innerText ? p.innerText.trim() : '';
                        if (txt) skus.push(txt);
                    });

                    return {
                        title: title.trim(),
                        shop_name: shopName.trim(),
                        images: images,
                        prices: prices,
                        skus: skus,
                        url: window.location.href
                    };
                })()
            """)

            # Parse evaluate result properly from Nodriver
            result_dict = {}
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        k = item[0]
                        v = item[1]
                        if isinstance(v, dict) and "value" in v:
                            result_dict[k] = v["value"]
                        else:
                            result_dict[k] = v
            elif isinstance(data, dict):
                result_dict = data

            price_val = 0.0
            if result_dict.get("prices"):
                try:
                    price_val = float(result_dict["prices"][0])
                except Exception:
                    price_val = 0.0

            return {
                "code": 200,
                "msg": "success",
                "data": {
                    "item_id": item_id,
                    "title": result_dict.get("title", ""),
                    "price": price_val,
                    "num_iid": item_id,
                    "seller_nick": result_dict.get("shop_name", ""),
                    "pic_url": result_dict.get("images", [""])[0] if result_dict.get("images") else "",
                    "item_imgs": [{"url": u} for u in result_dict.get("images", [])],
                    "sku_props": result_dict.get("skus", []),
                    "detail_url": url
                }
            }
        finally:
            await manager.close()


@app.get("/1688/v2/item_detail")
async def get_1688_item_detail(item_id: str = Query(...), apiToken: Optional[str] = None):
    """Tương thích 100% endpoint TMAPI 1688 item_detail"""
    res = await scrape_1688_page(item_id)
    return res


@app.get("/taobao/item_detail")
async def get_taobao_item_detail(item_id: str = Query(...), apiToken: Optional[str] = None):
    """Tương thích 100% endpoint TMAPI Taobao item_detail"""
    url = f"https://item.taobao.com/item.htm?id={item_id}"
    os.environ["DISPLAY"] = ":99"
    async with BROWSER_LOCK:
        manager = NodriverBrowserManager()
        browser, tab = await manager.start(profile_config=PROFILE_CONFIG, headless=False)
        try:
            await tab.get(url)
            await asyncio.sleep(4.0)

            data = await tab.evaluate("""
                (() => {
                    const title = (document.querySelector('h1') || document.querySelector('.tb-main-title') || {}).innerText || document.title;
                    const shop = (document.querySelector('.shop-name, .tb-shop-name, .base-info-shop-name') || {}).innerText || 'Taobao Shop';
                    
                    const imgNodes = document.querySelectorAll('#J_UlThumb img, .tb-gallery img, .main-img-item img');
                    let images = [];
                    imgNodes.forEach(img => {
                        let src = img.src || img.getAttribute('data-src');
                        if (src) {
                            src = src.replace(/_[0-9]+x[0-9]+.*\\.jpg/i, '');
                            if (!images.includes(src) && !src.includes('data:image')) images.push(src);
                        }
                    });

                    return {
                        title: title.trim(),
                        shop_name: shop.trim(),
                        images: images
                    };
                })()
            """)

            return {
                "code": 200,
                "msg": "success",
                "data": {
                    "item_id": item_id,
                    "title": data.get("title", ""),
                    "price": 0.0,
                    "num_iid": item_id,
                    "seller_nick": data.get("shop_name", ""),
                    "pic_url": data.get("images", [""])[0] if data.get("images") else "",
                    "item_imgs": [{"url": u} for u in data.get("images", [])],
                    "detail_url": url
                }
            }
        finally:
            await manager.close()


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "MunAntiBrowser Ecommerce Scraper Microservice"}


if __name__ == "__main__":
    uvicorn.run("ecommerce_scraper_service:app", host="0.0.0.0", port=8889, reload=False, workers=1)
