// MunAntiBrowser - Canvas Fingerprint Noise
// Adds subtle noise to canvas operations to create unique fingerprints.
// Template: {{canvas_shift}} (JSON object with r, g, b, a values)

(function fakeCanvasFingerPrint() {
  const toBlob = HTMLCanvasElement.prototype.toBlob;
  const toDataURL = HTMLCanvasElement.prototype.toDataURL;
  const getImageData = CanvasRenderingContext2D.prototype.getImageData;

  // Capture helpers locally in closure to protect dynamic iframes
  const _localMakeNative = window._makeNative;
  const _localSafelyOverrideValue = window._safelyOverrideValue;

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

  var noisify = function (canvas, context) {
    if (context) {
      try {
        const shift = {{canvas_shift}};
        let ctxIdx = ctxArr.indexOf(context);
        let info = ctxInf[ctxIdx];
        const width = canvas.width;
        const height = canvas.height;
        if (info && (info.useArc || info.useFillText) && width && height) {
          const imageData = getImageData.apply(context, [0, 0, width, height]);
          for (let i = 0; i < height; i++) {
            for (let j = 0; j < width; j++) {
              const n = ((i * (width * 4)) + (j * 4));
              imageData.data[n + 0] = imageData.data[n + 0] + shift.r;
              imageData.data[n + 1] = imageData.data[n + 1] + shift.g;
              imageData.data[n + 2] = imageData.data[n + 2] + shift.b;
              imageData.data[n + 3] = imageData.data[n + 3] + shift.a;
            }
          }
          context.putImageData(imageData, 0, 0);
        }
      } catch (e) {
        // Silently ignore tainted canvas errors (cross-origin)
      }
    }
  };


  let ctxArr = [];
  let ctxInf = [];
  let rawGetContext = HTMLCanvasElement.prototype.getContext;

  let wrappedGetContext = function () {
    let result = rawGetContext.apply(this, arguments);
    if (arguments[0] === '2d') {
      ctxArr.push(result);
      ctxInf.push({});
    }
    return result;
  };
  patchMethod(HTMLCanvasElement.prototype, "getContext", wrappedGetContext, rawGetContext.length);

  let rawArc = CanvasRenderingContext2D.prototype.arc;
  let wrappedArc = function () {
    let ctxIdx = ctxArr.indexOf(this);
    if (ctxIdx !== -1) {
      ctxInf[ctxIdx].useArc = true;
    }
    return rawArc.apply(this, arguments);
  };
  patchMethod(CanvasRenderingContext2D.prototype, "arc", wrappedArc, rawArc.length);

  const rawFillText = CanvasRenderingContext2D.prototype.fillText;
  let wrappedFillText = function () {
    let ctxIdx = ctxArr.indexOf(this);
    if (ctxIdx !== -1) {
      ctxInf[ctxIdx].useFillText = true;
    }
    return rawFillText.apply(this, arguments);
  };
  patchMethod(CanvasRenderingContext2D.prototype, "fillText", wrappedFillText, rawFillText.length);

  // toBlob override
  let wrappedToBlob = function () {
    noisify(this, this.getContext("2d"));
    return toBlob.apply(this, arguments);
  };
  patchMethod(HTMLCanvasElement.prototype, "toBlob", wrappedToBlob, toBlob.length);

  // toDataURL override
  let wrappedToDataURL = function () {
    noisify(this, this.getContext("2d"));
    return toDataURL.apply(this, arguments);
  };
  patchMethod(HTMLCanvasElement.prototype, "toDataURL", wrappedToDataURL, toDataURL.length);

  // getImageData override
  let wrappedGetImageData = function () {
    noisify(this.canvas, this);
    return getImageData.apply(this, arguments);
  };
  patchMethod(CanvasRenderingContext2D.prototype, "getImageData", wrappedGetImageData, getImageData.length);
})();
