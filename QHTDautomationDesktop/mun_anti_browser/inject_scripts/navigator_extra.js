// MunAntiBrowser - Navigator Extra Spoofing (v3)
// Comprehensive navigator/screen/window consistency spoofing.
// iphey.com cross-checks: screen dimensions, color depth, pixel ratio,
// connection info, device memory, battery, and more.

(function fakeNavigatorExtra() {
  'use strict';

  // ── Device Memory ──
  var seed = {{plugins_seed}} || 12345;
  var memoryValues = [4, 8, 16];
  var fakeMemory = memoryValues[seed % memoryValues.length];
  try {
    Object.defineProperty(navigator, 'deviceMemory', {
      get: function() { return fakeMemory; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // ── Languages (must be consistent with Accept-Language header) ──
  try {
    Object.defineProperty(navigator, 'languages', {
      get: function() { return Object.freeze(['en-US', 'en']); },
      configurable: true, enumerable: true
    });
    Object.defineProperty(navigator, 'language', {
      get: function() { return 'en-US'; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // ── Do Not Track ──
  try {
    Object.defineProperty(navigator, 'doNotTrack', {
      get: function() { return null; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // ── Cookie Enabled ──
  try {
    Object.defineProperty(navigator, 'cookieEnabled', {
      get: function() { return true; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // ── Max Touch Points (desktop = 0, mobile varies) ──
  try {
    var isMobile = /Mobile|Android|iPhone/.test(navigator.userAgent);
    Object.defineProperty(navigator, 'maxTouchPoints', {
      get: function() { return isMobile ? 5 : 0; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // ── document.hasFocus() ──
  try {
    Document.prototype.hasFocus = function() { return true; };
  } catch(e) {}

  // ── Screen consistency ──
  // iphey checks: screen.width, screen.height, screen.availWidth, screen.availHeight,
  //   screen.colorDepth, screen.pixelDepth, devicePixelRatio
  try {
    if (typeof screen !== 'undefined') {
      var sw = screen.width || 1920;
      var sh = screen.height || 1080;

      // availWidth/availHeight = screen size minus taskbar (typically 40px)
      Object.defineProperty(screen, 'availWidth', {
        get: function() { return sw; },
        configurable: true, enumerable: true
      });
      Object.defineProperty(screen, 'availHeight', {
        get: function() { return sh - 40; },
        configurable: true, enumerable: true
      });
      Object.defineProperty(screen, 'availLeft', {
        get: function() { return 0; },
        configurable: true, enumerable: true
      });
      Object.defineProperty(screen, 'availTop', {
        get: function() { return 0; },
        configurable: true, enumerable: true
      });

      // Color depth must be consistent (24 for most monitors)
      Object.defineProperty(screen, 'colorDepth', {
        get: function() { return 24; },
        configurable: true, enumerable: true
      });
      Object.defineProperty(screen, 'pixelDepth', {
        get: function() { return 24; },
        configurable: true, enumerable: true
      });

      // Screen orientation
      Object.defineProperty(screen, 'orientation', {
        get: function() {
          return {
            type: 'landscape-primary',
            angle: 0,
            onchange: null
          };
        },
        configurable: true, enumerable: true
      });
    }
  } catch(e) {}

  // ── devicePixelRatio consistency ──
  try {
    var dpr = 1;
    var ua = navigator.userAgent || '';
    if (/iPhone|iPad|iPod/.test(ua)) {
      dpr = /iPhone/.test(ua) ? 3 : 2;
    } else if (/Android/.test(ua)) {
      dpr = (seed % 2 === 0) ? 2 : 3;
    } else if (/Macintosh|Mac OS X/.test(ua)) {
      dpr = (seed % 3 === 0) ? 2 : 1;
    }
    Object.defineProperty(window, 'devicePixelRatio', {
      get: function() { return dpr; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // ── window dimensions consistency ──
  try {
    // outerWidth/outerHeight should be close to screen dimensions
    var sw2 = screen.width || 1920;
    var sh2 = screen.height || 1080;
    
    Object.defineProperty(window, 'outerWidth', {
      get: function() { return sw2; },
      configurable: true, enumerable: true
    });
    Object.defineProperty(window, 'outerHeight', {
      get: function() { return sh2; },
      configurable: true, enumerable: true
    });
    
    // innerWidth/innerHeight = viewport (minus scrollbar/toolbars)
    if (window.innerWidth === 0 || window.innerHeight === 0) {
      Object.defineProperty(window, 'innerWidth', {
        get: function() { return sw2; },
        configurable: true
      });
      Object.defineProperty(window, 'innerHeight', {
        get: function() { return sh2 - 85; },
        configurable: true
      });
    }
    
    // screenX/screenY
    Object.defineProperty(window, 'screenX', {
      get: function() { return 0; },
      configurable: true, enumerable: true
    });
    Object.defineProperty(window, 'screenY', {
      get: function() { return 0; },
      configurable: true, enumerable: true
    });
    Object.defineProperty(window, 'screenLeft', {
      get: function() { return 0; },
      configurable: true, enumerable: true
    });
    Object.defineProperty(window, 'screenTop', {
      get: function() { return 0; },
      configurable: true, enumerable: true
    });
  } catch(e) {}

  // ── Visibility API ──
  try {
    Object.defineProperty(document, 'hidden', {
      get: function() { return false; },
      configurable: true
    });
    Object.defineProperty(document, 'visibilityState', {
      get: function() { return 'visible'; },
      configurable: true
    });
  } catch(e) {}

  // ── Performance.memory (Chrome-specific) ──
  try {
    if (typeof performance !== 'undefined') {
      var memGB = fakeMemory * 1073741824;
      Object.defineProperty(performance, 'memory', {
        get: function() {
          return {
            jsHeapSizeLimit: memGB,
            totalJSHeapSize: Math.floor(memGB * 0.7),
            usedJSHeapSize: Math.floor(memGB * 0.3)
          };
        },
        configurable: true
      });
    }
  } catch(e) {}

  // ── Connection API consistency ──
  try {
    if (navigator.connection) {
      Object.defineProperty(navigator.connection, 'effectiveType', {
        get: function() { return '4g'; },
        configurable: true, enumerable: true
      });
      Object.defineProperty(navigator.connection, 'rtt', {
        get: function() { return 50; },
        configurable: true, enumerable: true
      });
      Object.defineProperty(navigator.connection, 'downlink', {
        get: function() { return 10; },
        configurable: true, enumerable: true
      });
      Object.defineProperty(navigator.connection, 'saveData', {
        get: function() { return false; },
        configurable: true, enumerable: true
      });
    }
  } catch(e) {}

  // ── Notification permission safe check ──
  try {
    if (typeof Notification !== 'undefined' && navigator.permissions && navigator.permissions.query) {
      var origQuery = navigator.permissions.query.bind(navigator.permissions);
      navigator.permissions.query = function(parameters) {
        if (parameters && parameters.name === 'notifications') {
          return Promise.resolve({
            state: Notification.permission || 'default',
            onchange: null
          });
        }
        return origQuery(parameters);
      };
    }
  } catch(e) {}

  // ── Iframe contentWindow consistency ──
  // Some detectors check if properties differ inside iframes
  try {
    var origContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
    // Don't override - just ensure consistency is maintained
  } catch(e) {}

})();
