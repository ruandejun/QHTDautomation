// MunAntiBrowser - ClientRects Fingerprint Offset
// Offsets getClientRects and getBoundingClientRect to create unique fingerprint.
// Template: {{rects}} (float offset value)

(function() {
  'use strict';

  // Capture helpers locally in closure to protect dynamic iframes
  const _localMakeNative = window._makeNative;
  const _localSafelyOverrideValue = window._safelyOverrideValue;

  var doneFrames = new WeakSet();
  var off = {{rects}};
  var roundedRects = new WeakSet();
  var rawRects = new WeakSet();

  function applyRects(frame) {
    if (!frame) {
      return;
    }

    try {
      if (doneFrames.has(frame)) {
        return;
      }
      doneFrames.add(frame);
    } catch(e) {
      return; // Cross-origin window
    }

    function patchMethod(obj, prop, newFunc, len) {
      if (len !== undefined) {
        try {
          Object.defineProperty(newFunc, 'length', {
            value: len,
            configurable: true
          });
        } catch(e) {}
      }
      if (_localSafelyOverrideValue) {
        _localSafelyOverrideValue(obj, prop, newFunc);
      } else {
        try {
          Object.defineProperty(newFunc, 'name', {
            value: prop,
            configurable: true
          });
        } catch(e) {}
        if (_localMakeNative) {
          _localMakeNative(newFunc, prop);
        }
        try {
          Object.defineProperty(obj, prop, {
            value: newFunc,
            writable: true,
            configurable: true,
            enumerable: true
          });
        } catch(e) {}
      }
    }

    // Override DOMRectReadOnly.prototype getters in the frame context
    try {
      if (frame.DOMRectReadOnly && frame.DOMRectReadOnly.prototype) {
        const props = ["top", "right", "bottom", "left", "width", "height", "x", "y"];
        props.forEach(prop => {
          let origDesc = Object.getOwnPropertyDescriptor(frame.DOMRectReadOnly.prototype, prop);
          if (!origDesc || !origDesc.get) return;
          if (origDesc.get._isWrapped) return;

          let wrappedGetter = function() {
            let val = origDesc.get.call(this);
            if (roundedRects.has(this)) {
              return val + Math.round(off);
            } else if (rawRects.has(this)) {
              return val + off;
            }
            return val;
          };
          wrappedGetter._isWrapped = true;

          // Define the name of the function properly
          try {
            Object.defineProperty(wrappedGetter, 'name', {
              value: 'get ' + prop,
              configurable: true
            });
          } catch(e) {}

          // Spoof toString() for getter using native map
          if (_localMakeNative) {
            _localMakeNative(wrappedGetter, "get " + prop);
          }

          Object.defineProperty(frame.DOMRectReadOnly.prototype, prop, {
            get: wrappedGetter,
            configurable: true,
            enumerable: true
          });
        });
      }
    } catch(e) {}

    function getClientRectsProtection(el){
      if (window.location.host === "docs.google.com") return;
      let clientRects = frame[el].prototype.getClientRects;
      let wrappedGetClientRects = function() {
        let rects = clientRects.apply(this, arguments);
        if (rects) {
          for (let i = 0; i < rects.length; i++) {
            rawRects.add(rects[i]);
          }
        }
        return rects;
      };
      patchMethod(frame[el].prototype, "getClientRects", wrappedGetClientRects, clientRects.length);
    }

    function getBoundingClientRectsProtection(el){
      let boundingRects = frame[el].prototype.getBoundingClientRect;
      let wrappedGetBoundingClientRect = function() {
        let rect = boundingRects.apply(this, arguments);
        if (rect) {
          roundedRects.add(rect);
        }
        return rect;
      };
      patchMethod(frame[el].prototype, "getBoundingClientRect", wrappedGetBoundingClientRect, boundingRects.length);
    }

    ["Element", "Range"].forEach(function(el){
      if (frame[el] === undefined) return;
      getClientRectsProtection(el);
      getBoundingClientRectsProtection(el);
    });
  }

  applyRects(window);

  // Apply to iframes
  ["HTMLIFrameElement", "HTMLFrameElement"].forEach(function(el) {
    if (!self[el]) return;
    var wind = self[el].prototype.__lookupGetter__('contentWindow'),
        cont = self[el].prototype.__lookupGetter__('contentDocument');

    Object.defineProperties(self[el].prototype, {
      contentWindow: {
        get: function(){
          if (this.src && this.src.indexOf('//') !== -1 && location.host !== this.src.split('/')[2]) return wind.apply(this);
          let frame = wind.apply(this);
          if (frame) applyRects(frame);
          return frame;
        }
      },
      contentDocument: {
        get: function(){
          if (this.src && this.src.indexOf('//') !== -1 && location.host !== this.src.split('/')[2]) return cont.apply(this);
          let frame = cont.apply(this);
          if (frame) applyRects(frame);
          return frame;
        }
      }
    });
  });

})();
