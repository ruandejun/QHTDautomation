// MunAntiBrowser - CloudFlare Bypass & Automation Evasion (Enhanced v2)
// Comprehensive anti-detection: removes CF artifacts, hides automation
// flags, patches plugins, permissions, and prototype chain leaks.
// Injected BEFORE any page JS executes via Page.addScriptToEvaluateOnNewDocument.

(function antiDetectInit() {
  'use strict';

  // Setup native toString spoofing early so all subsequent patches can use it
  var _origToString = Function.prototype.toString;
  var _cache = new WeakMap();
  var _boundMap = new WeakMap();

  Function.prototype.toString = function() {
    if (_cache.has(this)) {
      return _cache.get(this);
    }
    return _origToString.call(this);
  };

  // Helper to make a function look native
  window._makeNative = function(fn, name) {
    _cache.set(fn, 'function ' + (name || fn.name || '') + '() { [native code] }');
  };

  // Make toString itself look native
  _cache.set(Function.prototype.toString, 'function toString() { [native code] }');

  // Trace bound functions to bypass bind-based console serialisation traps
  var origBind = Function.prototype.bind;
  Function.prototype.bind = function(thisArg) {
    var boundFn = origBind.apply(this, arguments);
    try {
      var target = this;
      var depth = 0;
      while (_boundMap.has(target) && depth < 10) {
        target = _boundMap.get(target);
        depth++;
      }
      _boundMap.set(boundFn, target);
    } catch(e) {}
    return boundFn;
  };
  window._makeNative(Function.prototype.bind, 'bind');

  // Secure property and method overrides
  window._safelyOverrideGetter = function(obj, prop, getterVal) {
    var fn = typeof getterVal === 'function' ? getterVal : function() { return getterVal; };
    try {
      Object.defineProperty(fn, 'name', {
        value: 'get ' + prop,
        configurable: true
      });
    } catch (e) {}
    window._makeNative(fn, 'get ' + prop);
    try {
      Object.defineProperty(obj, prop, {
        get: fn,
        configurable: true,
        enumerable: true
      });
    } catch (e) {}
  };

  window._safelyOverrideValue = function(obj, prop, valueVal) {
    if (typeof valueVal === 'function') {
      try {
        Object.defineProperty(valueVal, 'name', {
          value: prop,
          configurable: true
        });
      } catch (e) {}
      window._makeNative(valueVal, prop);
    }
    try {
      Object.defineProperty(obj, prop, {
        value: valueVal,
        writable: true,
        configurable: true,
        enumerable: true
      });
    } catch (e) {}
  };

  // ============================================================
  // Intercept console calls to prevent CDP/DevTools object serialization checks (hasCDP bypass)
  // ============================================================
  (function hookConsole() {
    var originalConsole = {};
    var toStringFn = Function.prototype.toString;

    // Helper to calculate complexity score of an object to detect large payloads
    function getComplexity(obj, depth) {
      if (depth > 2) return 1000;
      if (!obj || typeof obj !== 'object') return 1;
      try {
        var keys = Object.keys(obj);
        var score = keys.length;
        for (var i = 0; i < keys.length; i++) {
          if (typeof obj[keys[i]] === 'object') {
            score += getComplexity(obj[keys[i]], depth + 1);
          }
        }
        return score;
      } catch (e) {
        return 1000; // Suspect circular or proxy
      }
    }

    for (var method in console) {
      try {
        if (typeof console[method] === 'function') {
          originalConsole[method] = console[method].bind(console);
          (function(m) {
            console[m] = function() {
              // Devtools performance checkers use table, log, clear
              // If we are calling table or clear, completely bypass to make it 0ms
              if (m === 'table' || m === 'clear') {
                return;
              }

              var args = Array.prototype.slice.call(arguments);
              var isBypassed = false;
              
              for (var idx = 0; idx < args.length; idx++) {
                var arg = args[idx];
                if (arg && (typeof arg === 'object' || typeof arg === 'function')) {
                  try {
                    // Check complexity of the logged argument
                    // If the argument is too large (like the performance test payload), bypass console print to avoid serialization overhead
                    if (getComplexity(arg, 0) > 100) {
                      isBypassed = true;
                      break;
                    }

                    var isSuspicious = false;
                    
                    // Check custom toString override (very common in hasCDP / devtools toString tests)
                    if (arg.toString && typeof arg.toString === 'function') {
                      try {
                        var toStringStr = toStringFn.call(arg.toString);
                        if (toStringStr.indexOf('[native code]') === -1) {
                          isSuspicious = true;
                        }
                      } catch (e) {
                        isSuspicious = true;
                      }
                    }

                    // Special rule for Error objects (D5/I5 bypass)
                    // Standard Error instances only have data properties (e.g. stack/name are strings).
                    // If any getter exists directly on the instance, it is 100% a serialization trap.
                    if (!isSuspicious && (arg instanceof Error || Object.prototype.toString.call(arg) === '[object Error]')) {
                      try {
                        var ownProps = Object.getOwnPropertyNames(arg);
                        for (var k = 0; k < ownProps.length; k++) {
                          var ownDesc = Object.getOwnPropertyDescriptor(arg, ownProps[k]);
                          if (ownDesc && ownDesc.get) {
                            isSuspicious = true;
                            break;
                          }
                        }
                      } catch (e) {
                        isSuspicious = true;
                      }
                    }

                    if (!isSuspicious) {
                      // Check self properties for custom getters
                      try {
                        var props = Object.getOwnPropertyNames(arg);
                        for (var i = 0; i < props.length; i++) {
                          var desc = Object.getOwnPropertyDescriptor(arg, props[i]);
                          if (desc && desc.get) {
                            var getterFn = desc.get;
                            // Transitively resolve bound getter functions with depth limit
                            var depthSelf = 0;
                            while (_boundMap.has(getterFn) && depthSelf < 10) {
                              getterFn = _boundMap.get(getterFn);
                              depthSelf++;
                            }
                            var getStr = toStringFn.call(getterFn);
                            if (getStr.indexOf('[native code]') === -1) {
                              isSuspicious = true;
                              break;
                            }
                          }
                        }
                      } catch (e) {
                        isSuspicious = true;
                      }
                    }

                    if (!isSuspicious) {
                      // Check prototype properties
                      try {
                        var proto = Object.getPrototypeOf(arg);
                        while (proto && proto !== Object.prototype) {
                          var protoProps = Object.getOwnPropertyNames(proto);
                          for (var j = 0; j < protoProps.length; j++) {
                            var pDesc = Object.getOwnPropertyDescriptor(proto, protoProps[j]);
                            if (pDesc && pDesc.get) {
                              var pGetterFn = pDesc.get;
                              // Transitively resolve bound getter functions with depth limit
                              var depthProto = 0;
                              while (_boundMap.has(pGetterFn) && depthProto < 10) {
                                pGetterFn = _boundMap.get(pGetterFn);
                                depthProto++;
                              }
                              var pGetStr = toStringFn.call(pGetterFn);
                              if (pGetStr.indexOf('[native code]') === -1) {
                                isSuspicious = true;
                                break;
                              }
                            }
                          }
                          if (isSuspicious) break;
                          proto = Object.getPrototypeOf(proto);
                        }
                      } catch (e) {
                        isSuspicious = true;
                      }
                    }
                    if (isSuspicious) {
                      isBypassed = true;
                      break;
                    }
                  } catch (e) {}
                }
              }

              if (isBypassed) {
                return; // Entirely skip print to prevent CDP serialization and getter calls
              }

              return originalConsole[m].apply(console, args);
            };
            if (window._makeNative) {
              window._makeNative(console[m], m);
            }
          })(method);
        }
      } catch (e) {}
    }
  })();

  // ============================================================
  // Intercept Web Worker creation to bypass worker-performance checkers
  // ============================================================
  (function hookBlobAndWorker() {
    var OriginalBlob = window.Blob;
    var NewBlob = function(parts, options) {
      if (parts && parts.length > 0) {
        for (var i = 0; i < parts.length; i++) {
          if (typeof parts[i] === 'string' && 
              parts[i].indexOf('console[action.type]') !== -1 && 
              parts[i].indexOf('performance.now()') !== -1) {
            // Prepend console and performance fakers inside the worker script to return exactly 0ms
            var faker = "self.console = { log: function(){}, table: function(){}, clear: function(){} };\n" +
                        "try { Object.defineProperty(self, 'performance', { value: { now: function() { return 100; } }, configurable: true }); } catch(e) {}\n";
            parts[i] = faker + parts[i];
            break;
          }
        }
      }
      return new OriginalBlob(parts, options);
    };
    NewBlob.prototype = OriginalBlob.prototype;
    window.Blob = NewBlob;
    if (window._makeNative) {
      window._makeNative(window.Blob, 'Blob');
    }

    var OriginalWorker = window.Worker;
    var NewWorker = function(scriptURL, options) {
      if (typeof scriptURL === 'string' && scriptURL.indexOf('data:text/javascript') === 0) {
        try {
          var commaIdx = scriptURL.indexOf(',');
          if (commaIdx !== -1) {
            var isBase64 = scriptURL.substring(0, commaIdx).indexOf('base64') !== -1;
            var payload = scriptURL.substring(commaIdx + 1);
            var decoded = isBase64 ? atob(payload) : decodeURIComponent(payload);
            if (decoded.indexOf('console[action.type]') !== -1 && 
                decoded.indexOf('performance.now()') !== -1) {
              var faker = "self.console = { log: function(){}, table: function(){}, clear: function(){} };\n" +
                          "try { Object.defineProperty(self, 'performance', { value: { now: function() { return 100; } }, configurable: true }); } catch(e) {}\n";
              decoded = faker + decoded;
              var newPayload = isBase64 ? btoa(decoded) : encodeURIComponent(decoded);
              scriptURL = scriptURL.substring(0, commaIdx + 1) + newPayload;
            }
          }
        } catch (e) {}
      }
      return new OriginalWorker(scriptURL, options);
    };
    NewWorker.prototype = OriginalWorker.prototype;
    window.Worker = NewWorker;
    if (window._makeNative) {
      window._makeNative(window.Worker, 'Worker');
    }
  })();

  // ============================================================
  // 1. Remove CDP / automation leak properties from window
  //    CF checks for properties matching patterns like cdc_, $chrome_, etc.
  // ============================================================
  (function removeCDPLeaks() {
    // Immediate cleanup
    var keysToRemove = [];
    try {
      var obj = window;
      while (obj !== null) {
        Object.getOwnPropertyNames(obj).forEach(function(prop) {
          if (
            prop.match(/.+_.+_(Array|Promise|Symbol|Object|Proxy)/ig) ||
            prop.match(/^cdc_/i) ||
            prop.match(/^\$cdc_/i) ||
            prop.match(/^\$chrome_asyncScriptInfo/i) ||
            prop.match(/^__webdriver/i) ||
            prop.match(/^__selenium/i) ||
            prop.match(/^__fxdriver/i) ||
            prop.match(/^__driver/i) ||
            prop.match(/^_selenium/i) ||
            prop.match(/^calledSelenium/i) ||
            prop.match(/^domAutomation/i)
          ) {
            keysToRemove.push(prop);
          }
        });
        obj = Object.getPrototypeOf(obj);
      }
    } catch (e) {}

    // Add explicit check for domAutomation and domAutomationController
    if ('domAutomation' in window) keysToRemove.push('domAutomation');
    if ('domAutomationController' in window) keysToRemove.push('domAutomationController');

    keysToRemove.forEach(function(key) {
      try { delete window[key]; } catch (e) {}
    });

    // Also cleanup on DOMContentLoaded (some leaks appear later)
    if (typeof document !== 'undefined') {
      document.addEventListener('DOMContentLoaded', function() {
        var obj2 = window, result = [];
        while (obj2 !== null) {
          try {
            result = result.concat(Object.getOwnPropertyNames(obj2));
          } catch (e) {}
          obj2 = Object.getPrototypeOf(obj2);
        }
        result.forEach(function(p) {
          if (p.match(/.+_.+_(Array|Promise|Symbol|Object|Proxy)/ig)) {
            try { delete window[p]; } catch (e) {}
          }
        });
      });
    }
  })();

  // ============================================================
  // 2. navigator.webdriver = undefined (not false!)
  //    Chrome's C++ code sets webdriver AFTER addScriptToEvaluateOnNewDocument.
  //    We use multiple deferred strategies to override after Chrome.
  //    CF checks: typeof navigator.webdriver !== 'undefined'
  // ============================================================
  (function patchWebdriver() {
    var _setWebdriverUndefined = function() {
      try { delete navigator.webdriver; } catch (e) {}
      try { delete Navigator.prototype.webdriver; } catch (e) {}
    };

    // Immediate attempt
    _setWebdriverUndefined();

    // Deferred: run after Chrome's internal webdriver setup
    // Use multiple timing strategies for reliability
    if (typeof requestAnimationFrame !== 'undefined') {
      requestAnimationFrame(_setWebdriverUndefined);
    }
    setTimeout(_setWebdriverUndefined, 0);
    setTimeout(_setWebdriverUndefined, 1);
    setTimeout(_setWebdriverUndefined, 10);

    // Also override on DOM ready
    if (typeof document !== 'undefined') {
      document.addEventListener('DOMContentLoaded', _setWebdriverUndefined);
    }
  })();



  // ============================================================
  // 3. navigator.plugins & navigator.mimeTypes - Native-compliant spoofing
  //    Empty plugins array or non-standard structure = headless detection.
  //    Must spoof: Plugin, MimeType, PluginArray, MimeTypeArray,
  //    and ensure prototypes match exactly so instanceof checks work.
  // ============================================================
  (function fakePluginsAndMimeTypes() {
    // Seeded random number generator
    var seed = {{plugins_seed}} || 12345;
    function seededRandom() {
      var x = Math.sin(seed++) * 10000;
      return x - Math.floor(x);
    }

    // Shuffle helper
    function seededShuffle(arr) {
      for (var i = arr.length - 1; i > 0; i--) {
        var j = Math.floor(seededRandom() * (i + 1));
        var temp = arr[i];
        arr[i] = arr[j];
        arr[j] = temp;
      }
      return arr;
    }

    var basePlugins = [
      {
        name: 'PDF Viewer',
        description: 'Portable Document Format',
        filename: 'internal-pdf-viewer',
        mimeTypes: [
          { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
          { type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
        ]
      },
      {
        name: 'Chrome PDF Viewer',
        description: 'Portable Document Format',
        filename: 'internal-pdf-viewer',
        mimeTypes: [
          { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
        ]
      },
      {
        name: 'Chromium PDF Viewer',
        description: 'Portable Document Format',
        filename: 'internal-pdf-viewer',
        mimeTypes: [
          { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
        ]
      },
      {
        name: 'Microsoft Edge PDF Viewer',
        description: 'Portable Document Format',
        filename: 'internal-pdf-viewer',
        mimeTypes: [
          { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
        ]
      },
      {
        name: 'WebKit built-in PDF',
        description: 'Portable Document Format',
        filename: 'internal-pdf-viewer',
        mimeTypes: [
          { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
        ]
      }
    ];

    // Optional plugins to vary the counts/hashes
    var optionalPlugins = [
      {
        name: 'Widevine Content Decryption Module',
        description: 'Enables Widevine licenses for playback of HTML audio/video content.',
        filename: 'widevinecdm.dll',
        mimeTypes: [
          { type: 'application/x-ppapi-widevine-cdm', suffixes: '', description: 'Widevine Content Decryption Module' }
        ]
      },
      {
        name: 'Native Client',
        description: '',
        filename: 'internal-nacl-plugin',
        mimeTypes: [
          { type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable' },
          { type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable' }
        ]
      }
    ];

    // Shuffle the base PDF plugins to change the order/hash
    var fakeData = seededShuffle(basePlugins.slice());

    // Randomly add optional plugins based on the seed
    optionalPlugins.forEach(function(optPlugin) {
      if (seededRandom() > 0.5) {
        fakeData.push(optPlugin);
      }
    });

    // Shuffle one last time
    fakeData = seededShuffle(fakeData);


    // Helper to generate native-like toString
    var makeToString = function(name) {
      return function() {
        return 'function ' + name + '() { [native code] }';
      };
    };

    // Construct raw native-like objects
    var pluginsList = [];
    var mimeTypesList = [];

    // Helper to define properties exactly as Chrome does (enumerable, read-only unless configured)
    var defineReadOnly = function(obj, prop, val) {
      Object.defineProperty(obj, prop, {
        value: val,
        writable: false,
        enumerable: true,
        configurable: true
      });
    };

    fakeData.forEach(function(pData) {
      // 1. Create Plugin instance
      var plugin = Object.create(Plugin.prototype);
      defineReadOnly(plugin, 'name', pData.name);
      defineReadOnly(plugin, 'description', pData.description);
      defineReadOnly(plugin, 'filename', pData.filename);
      defineReadOnly(plugin, 'length', pData.mimeTypes.length);

      var pluginMimeTypes = [];

      pData.mimeTypes.forEach(function(mData) {
        // 2. Create MimeType instance
        var mimeType = Object.create(MimeType.prototype);
        defineReadOnly(mimeType, 'type', mData.type);
        defineReadOnly(mimeType, 'suffixes', mData.suffixes);
        defineReadOnly(mimeType, 'description', mData.description);
        defineReadOnly(mimeType, 'enabledPlugin', plugin);

        // Map type on the Plugin instance itself
        defineReadOnly(plugin, mData.type, mimeType);
        pluginMimeTypes.push(mimeType);

        // Add to global mimeTypes list if not already present
        var exists = mimeTypesList.some(function(m) { return m.type === mData.type; });
        if (!exists) {
          mimeTypesList.push(mimeType);
        }
      });

      // Implement item/namedItem on Plugin
      plugin.item = function(index) {
        return pluginMimeTypes[index] || null;
      };
      plugin.namedItem = function(type) {
        for (var idx = 0; idx < pluginMimeTypes.length; idx++) {
          if (pluginMimeTypes[idx].type === type) return pluginMimeTypes[idx];
        }
        return null;
      };
      if (window._makeNative) {
        window._makeNative(plugin.item, 'item');
        window._makeNative(plugin.namedItem, 'namedItem');
      } else {
        plugin.item.toString = makeToString('item');
        plugin.namedItem.toString = makeToString('namedItem');
      }

      // Map numerical index properties to Plugin
      pluginMimeTypes.forEach(function(mt, idx) {
        defineReadOnly(plugin, idx, mt);
      });

      pluginsList.push(plugin);
    });

    // Create PluginArray instance
    var pluginArray = Object.create(PluginArray.prototype);
    defineReadOnly(pluginArray, 'length', pluginsList.length);
    pluginsList.forEach(function(pl, idx) {
      defineReadOnly(pluginArray, idx, pl);
      defineReadOnly(pluginArray, pl.name, pl);
    });

    pluginArray.item = function(index) {
      return pluginsList[index] || null;
    };
    pluginArray.namedItem = function(name) {
      for (var idx = 0; idx < pluginsList.length; idx++) {
        if (pluginsList[idx].name === name) return pluginsList[idx];
      }
      return null;
    };
    pluginArray.refresh = function() {};
    
    if (window._makeNative) {
      window._makeNative(pluginArray.item, 'item');
      window._makeNative(pluginArray.namedItem, 'namedItem');
      window._makeNative(pluginArray.refresh, 'refresh');
    } else {
      pluginArray.item.toString = makeToString('item');
      pluginArray.namedItem.toString = makeToString('namedItem');
      pluginArray.refresh.toString = makeToString('refresh');
    }

    // Create MimeTypeArray instance
    var mimeTypeArray = Object.create(MimeTypeArray.prototype);
    defineReadOnly(mimeTypeArray, 'length', mimeTypesList.length);
    mimeTypesList.forEach(function(mt, idx) {
      defineReadOnly(mimeTypeArray, idx, mt);
      defineReadOnly(mimeTypeArray, mt.type, mt);
    });

    mimeTypeArray.item = function(index) {
      return mimeTypesList[index] || null;
    };
    mimeTypeArray.namedItem = function(type) {
      for (var idx = 0; idx < mimeTypesList.length; idx++) {
        if (mimeTypesList[idx].type === type) return mimeTypesList[idx];
      }
      return null;
    };

    if (window._makeNative) {
      window._makeNative(mimeTypeArray.item, 'item');
      window._makeNative(mimeTypeArray.namedItem, 'namedItem');
    } else {
      mimeTypeArray.item.toString = makeToString('item');
      mimeTypeArray.namedItem.toString = makeToString('namedItem');
    }

    // Create empty arrays for mobile / non-Chrome environments to avoid detection
    var emptyPluginArray = Object.create(PluginArray.prototype);
    defineReadOnly(emptyPluginArray, 'length', 0);
    emptyPluginArray.item = function(index) { return null; };
    emptyPluginArray.namedItem = function(name) { return null; };
    emptyPluginArray.refresh = function() {};
    
    var emptyMimeTypeArray = Object.create(MimeTypeArray.prototype);
    defineReadOnly(emptyMimeTypeArray, 'length', 0);
    emptyMimeTypeArray.item = function(index) { return null; };
    emptyMimeTypeArray.namedItem = function(name) { return null; };

    if (window._makeNative) {
      window._makeNative(emptyPluginArray.item, 'item');
      window._makeNative(emptyPluginArray.namedItem, 'namedItem');
      window._makeNative(emptyPluginArray.refresh, 'refresh');
      window._makeNative(emptyMimeTypeArray.item, 'item');
      window._makeNative(emptyMimeTypeArray.namedItem, 'namedItem');
    } else {
      emptyPluginArray.item.toString = makeToString('item');
      emptyPluginArray.namedItem.toString = makeToString('namedItem');
      emptyPluginArray.refresh.toString = makeToString('refresh');
      emptyMimeTypeArray.item.toString = makeToString('item');
      emptyMimeTypeArray.namedItem.toString = makeToString('namedItem');
    }

    // Helper to check if current User-Agent corresponds to mobile or Firefox
    var getMocksForCurrentUA = function(winObj) {
      var targetWin = winObj || window;
      var ua = targetWin.navigator.userAgent || '';
      var isMobile = /Mobile|Android|iPhone|iPad/.test(ua);
      var isFirefox = ua.indexOf('Firefox') !== -1;
      if (isMobile || isFirefox) {
        return { plugins: emptyPluginArray, mimeTypes: emptyMimeTypeArray };
      }
      return { plugins: pluginArray, mimeTypes: mimeTypeArray };
    };

    // Build getter functions
    var pluginsGetter = function() { return getMocksForCurrentUA().plugins; };
    var mimeTypesGetter = function() { return getMocksForCurrentUA().mimeTypes; };
    window._makeNative(pluginsGetter, 'get plugins');
    window._makeNative(mimeTypesGetter, 'get mimeTypes');

    // 1. Override on Navigator.prototype FIRST (prevents bypass via prototype getter)
    try {
      Object.defineProperty(Navigator.prototype, 'plugins', {
        get: pluginsGetter,
        configurable: true,
        enumerable: true
      });
      Object.defineProperty(Navigator.prototype, 'mimeTypes', {
        get: mimeTypesGetter,
        configurable: true,
        enumerable: true
      });
    } catch (e) {}

    // 2. DO NOT override on navigator instance - native Chrome only has getters
    //    on Navigator.prototype, not on the navigator instance itself.
    //    Overriding on instance creates detectable "instance getters" leak.

    // 3. Protect Object.getOwnPropertyDescriptor so it returns our fake getter
    //    This prevents detection via:
    //    Object.getOwnPropertyDescriptor(Navigator.prototype, 'plugins').get.call(navigator)
    var origGetOwnPropDesc = Object.getOwnPropertyDescriptor;
    var gopdProxy = function(obj, prop) {
      if ((obj === Navigator.prototype || obj === navigator) &&
          (prop === 'plugins' || prop === 'mimeTypes')) {
        return {
          get: prop === 'plugins' ? pluginsGetter : mimeTypesGetter,
          set: undefined,
          enumerable: true,
          configurable: true
        };
      }
      return origGetOwnPropDesc.call(Object, obj, prop);
    };
    window._makeNative(gopdProxy, 'getOwnPropertyDescriptor');
    Object.getOwnPropertyDescriptor = gopdProxy;

    // 4. Persist mock inside HTMLIFrameElement context Window when created
    try {
      var origContentWindow = origGetOwnPropDesc.call(Object,
        HTMLIFrameElement.prototype, 'contentWindow'
      );
      if (origContentWindow && origContentWindow.get) {
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
          get: function() {
            var win = origContentWindow.get.call(this);
            if (win) {
              try {
                var iframePluginsGetter = function() { return getMocksForCurrentUA(win).plugins; };
                var iframeMimeGetter = function() { return getMocksForCurrentUA(win).mimeTypes; };
                // Override on the iframe's Navigator.prototype
                Object.defineProperty(win.Navigator.prototype, 'plugins', {
                  get: iframePluginsGetter,
                  configurable: true,
                  enumerable: true
                });
                Object.defineProperty(win.Navigator.prototype, 'mimeTypes', {
                  get: iframeMimeGetter,
                  configurable: true,
                  enumerable: true
                });
                // Override on the iframe's navigator instance
                Object.defineProperty(win.navigator, 'plugins', {
                  get: iframePluginsGetter,
                  configurable: true,
                  enumerable: true
                });
                Object.defineProperty(win.navigator, 'mimeTypes', {
                  get: iframeMimeGetter,
                  configurable: true,
                  enumerable: true
                });
              } catch (e) {}
            }
            return win;
          },
          configurable: true
        });
      }
    } catch (e) {}
  })();

  // ============================================================
  // 4. navigator.permissions.query - Consistent behavior
  //    CF checks that Notification.permission is consistent with
  //    permissions.query({name:'notifications'})
  // ============================================================
  (function patchPermissions() {
    if (navigator.permissions) {
      var originalQuery = navigator.permissions.query.bind(navigator.permissions);
      var queryProxy = function(parameters) {
        if (parameters && parameters.name === 'notifications') {
          return Promise.resolve({
            state: Notification.permission,
            onchange: null
          });
        }
        return originalQuery(parameters);
      };
      // Make toString look native using WeakMap-based _makeNative
      window._makeNative(queryProxy, 'query');
      try {
        Object.defineProperty(navigator.permissions, 'query', {
          value: queryProxy,
          configurable: true,
          writable: true
        });
      } catch (e) {}
    }
  })();

  // ============================================================
  // 5. window.chrome - Must exist with proper structure
  //    CF checks window.chrome.app, window.chrome.runtime
  // ============================================================
  (function patchChrome() {
    var chromeObj = {};
    
    // 1. app (enumerable)
    var getDetailsFn = function() { return null; };
    var getIsInstalledFn = function() { return false; };
    window._makeNative(getDetailsFn, 'getDetails');
    window._makeNative(getIsInstalledFn, 'getIsInstalled');
    chromeObj.app = {
      isInstalled: false,
      InstallState: {
        DISABLED: 'disabled',
        INSTALLED: 'installed',
        NOT_INSTALLED: 'not_installed'
      },
      RunningState: {
        CANNOT_RUN: 'cannot_run',
        READY_TO_RUN: 'ready_to_run',
        RUNNING: 'running'
      },
      getDetails: getDetailsFn,
      getIsInstalled: getIsInstalledFn
    };

    // 2. csi (enumerable)
    var csiFn = function() {
      return {
        onloadT: Date.now(),
        startE: Date.now(),
        pageT: Math.floor(Math.random() * 2000) + 500,
        tran: 15
      };
    };
    window._makeNative(csiFn, 'csi');
    chromeObj.csi = csiFn;

    // 3. loadTimes (enumerable)
    var loadTimesFn = function() {
      return {
        commitLoadTime: Date.now() / 1000,
        connectionInfo: 'h2',
        finishDocumentLoadTime: Date.now() / 1000 + 0.5,
        finishLoadTime: Date.now() / 1000 + 1,
        firstPaintAfterLoadTime: 0,
        firstPaintTime: Date.now() / 1000 + 0.3,
        navigationType: 'Other',
        npnNegotiatedProtocol: 'h2',
        requestTime: Date.now() / 1000 - 1,
        startLoadTime: Date.now() / 1000 - 0.5,
        wasAlternateProtocolAvailable: false,
        wasFetchedViaSpdy: true,
        wasNpnNegotiated: true
      };
    };
    window._makeNative(loadTimesFn, 'loadTimes');
    chromeObj.loadTimes = loadTimesFn;

    // 4. runtime (non-enumerable so it does not leak via Object.keys)
    var connectFn = function() {};
    var sendMessageFn = function() {};
    window._makeNative(connectFn, 'connect');
    window._makeNative(sendMessageFn, 'sendMessage');
    Object.defineProperty(chromeObj, 'runtime', {
      value: {
        connect: connectFn,
        sendMessage: sendMessageFn
      },
      enumerable: false,
      configurable: true,
      writable: true
    });

    window.chrome = chromeObj;
  })();

  // ============================================================
  // 6. Consistent screen dimensions
  //    window.outerWidth/outerHeight must relate to innerWidth/innerHeight
  // ============================================================
  (function patchScreenConsistency() {
    // Ensure outerWidth/Height are slightly larger than inner (toolbar/border)
    var _innerWidth = window.innerWidth;
    var _innerHeight = window.innerHeight;
    try {
      var owGetter = function() { return window.innerWidth; };
      var ohGetter = function() { return window.innerHeight + 85; };
      window._makeNative(owGetter, 'get outerWidth');
      window._makeNative(ohGetter, 'get outerHeight');
      Object.defineProperty(window, 'outerWidth', {
        get: owGetter,
        configurable: true
      });
      Object.defineProperty(window, 'outerHeight', {
        get: ohGetter, // Chrome toolbar ~85px
        configurable: true
      });
    } catch (e) {}
  })();
  // Helpers were moved to the top of the file to allow early usage.

  // ============================================================
  // 8. iframe contentWindow protection
  //    Ensure our spoofs persist into iframes (CF loads challenge in iframe)
  // ============================================================
  (function protectIframes() {
    // WeakSet to avoid re-patching the same iframe window
    var _patchedIframes = new WeakSet();

    function patchIframeWindow(win) {
      if (!win || _patchedIframes.has(win)) return;
      try { _patchedIframes.add(win); } catch(e) { return; }

      try {
        // 1. CRITICAL: Patch toString in iframe to use the same WeakMap cache
        //    This prevents detection via iframe.contentWindow.Function.prototype.toString.call(mainFn)
        win.Function.prototype.toString = function() {
          if (_cache.has(this)) {
            return _cache.get(this);
          }
          return _origToString.call(this);
        };
        _cache.set(win.Function.prototype.toString, 'function toString() { [native code] }');

        // 2. Patch bind in iframe
        var iframeOrigBind = win.Function.prototype.bind;
        win.Function.prototype.bind = function(thisArg) {
          var boundFn = iframeOrigBind.apply(this, arguments);
          try {
            var target = this;
            var depth = 0;
            while (_boundMap.has(target) && depth < 10) {
              target = _boundMap.get(target);
              depth++;
            }
            _boundMap.set(boundFn, target);
          } catch(e) {}
          return boundFn;
        };
        _cache.set(win.Function.prototype.bind, 'function bind() { [native code] }');

        // 3. Patch console in iframe to match main window console
        try {
          var methods = ['log', 'warn', 'error', 'info', 'debug', 'table', 'clear', 'dir', 'trace'];
          for (var mi = 0; mi < methods.length; mi++) {
            if (typeof console[methods[mi]] === 'function') {
              win.console[methods[mi]] = console[methods[mi]];
            }
          }
        } catch(e) {}

        // 4. Patch Blob in iframe
        try { win.Blob = Blob; } catch(e) {}
        try { win.Worker = Worker; } catch(e) {}

        // 5. Patch Object.getOwnPropertyDescriptor in iframe
        try { win.Object.getOwnPropertyDescriptor = Object.getOwnPropertyDescriptor; } catch(e) {}

        // 6. Patch webdriver in iframe
        try {
          delete win.navigator.webdriver;
          delete win.Navigator.prototype.webdriver;
        } catch(e) {}

      } catch(e) {} // Cross-origin iframes will throw - that's OK
    }

    // Hook HTMLIFrameElement.prototype.contentWindow
    try {
      var origContentWindow = Object.getOwnPropertyDescriptor(
        HTMLIFrameElement.prototype, 'contentWindow'
      );
      if (origContentWindow && origContentWindow.get) {
        var cwGetter = function() {
          var win = origContentWindow.get.call(this);
          if (win) patchIframeWindow(win);
          return win;
        };
        _cache.set(cwGetter, 'function get contentWindow() { [native code] }');
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
          get: cwGetter,
          configurable: true
        });
      }
    } catch (e) {}

    // Hook HTMLIFrameElement.prototype.contentDocument
    try {
      var origContentDoc = Object.getOwnPropertyDescriptor(
        HTMLIFrameElement.prototype, 'contentDocument'
      );
      if (origContentDoc && origContentDoc.get) {
        var cdGetter = function() {
          // Patch the window before returning document
          try {
            var win = this.contentWindow; // triggers cwGetter above
          } catch(e) {}
          return origContentDoc.get.call(this);
        };
        _cache.set(cdGetter, 'function get contentDocument() { [native code] }');
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentDocument', {
          get: cdGetter,
          configurable: true
        });
      }
    } catch (e) {}

    // Also hook document.createElement to patch iframes as soon as they're created
    var origCreateElement = document.createElement;
    document.createElement = function(tagName) {
      var el = origCreateElement.apply(this, arguments);
      if (tagName && tagName.toLowerCase() === 'iframe') {
        // Patch on load
        el.addEventListener('load', function() {
          try { patchIframeWindow(el.contentWindow); } catch(e) {}
        });
      }
      return el;
    };
    _cache.set(document.createElement, 'function createElement() { [native code] }');
  })();

  // ============================================================
  // 9. Prototype chain consistency
  //    Ensure getter/setter traps don't break hasOwnProperty checks
  // ============================================================
  (function fixPrototypeChain() {
    // Ensure Error.captureStackTrace exists (Chrome-specific)
    if (typeof Error.captureStackTrace !== 'function') {
      Error.captureStackTrace = function(obj, constructor) {
        obj.stack = new Error().stack;
      };
    }

    // Ensure window.chrome.runtime.PlatformOs exists
    try {
      if (window.chrome && window.chrome.runtime) {
        if (!window.chrome.runtime.PlatformOs) {
          window.chrome.runtime.PlatformOs = {
            MAC: 'mac', WIN: 'win', ANDROID: 'android',
            CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd'
          };
        }
        if (!window.chrome.runtime.PlatformArch) {
          window.chrome.runtime.PlatformArch = {
            ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64',
            MIPS: 'mips', MIPS64: 'mips64'
          };
        }
        if (!window.chrome.runtime.PlatformNaclArch) {
          window.chrome.runtime.PlatformNaclArch = {
            ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64',
            MIPS: 'mips', MIPS64: 'mips64'
          };
        }
        if (!window.chrome.runtime.RequestUpdateCheckStatus) {
          window.chrome.runtime.RequestUpdateCheckStatus = {
            THROTTLED: 'throttled',
            NO_UPDATE: 'no_update',
            UPDATE_AVAILABLE: 'update_available'
          };
        }
        if (!window.chrome.runtime.OnInstalledReason) {
          window.chrome.runtime.OnInstalledReason = {
            INSTALL: 'install', UPDATE: 'update',
            CHROME_UPDATE: 'chrome_update', SHARED_MODULE_UPDATE: 'shared_module_update'
          };
        }
        if (!window.chrome.runtime.OnRestartRequiredReason) {
          window.chrome.runtime.OnRestartRequiredReason = {
            APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic'
          };
        }
      }
    } catch (e) {}
  })();

})();
