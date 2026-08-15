(() => {
  'use strict';

  // 1. Gỡ bỏ hoàn toàn dấu vết WebDriver & CDP Runtime
  try {
    delete navigator.__proto__.webdriver;
    delete Object.getPrototypeOf(navigator).webdriver;
  } catch (e) {}

  Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true,
    enumerable: false
  });

  // 2. Mock chrome.runtime cho tương thích hoàn toàn với Browser thật
  if (!window.chrome) {
    window.chrome = {};
  }
  if (!window.chrome.runtime) {
    window.chrome.runtime = {
      connect: () => {},
      sendMessage: () => {},
      id: undefined
    };
  }

  // 3. Bảo vệ các hàm native khỏi bị phát hiện hook bởi SECSDK (Alibaba Security)
  const originalToString = Function.prototype.toString;
  Function.prototype.toString = function () {
    if (this === Function.prototype.toString) {
      return 'function toString() { [native code] }';
    }
    return originalToString.call(this);
  };

  // 4. Override DeviceMemory & HardwareConcurrency tự nhiên
  Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8,
    configurable: true
  });
  Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8,
    configurable: true
  });

  // 5. Ngăn Alibaba SECSDK nhận diện Headless / Xvfb Display
  Object.defineProperty(window.screen, 'colorDepth', { get: () => 24 });
  Object.defineProperty(window.screen, 'pixelDepth', { get: () => 24 });

})();
