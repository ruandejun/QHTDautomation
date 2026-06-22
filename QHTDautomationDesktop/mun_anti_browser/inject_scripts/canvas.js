// MunAntiBrowser - Canvas Fingerprint Noise
// Adds subtle noise to canvas operations to create unique fingerprints.
// Template: {{canvas_shift}} (JSON object with r, g, b, a values)

(function fakeCanvasFingerPrint() {
  const toBlob = HTMLCanvasElement.prototype.toBlob;
  const toDataURL = HTMLCanvasElement.prototype.toDataURL;
  const getImageData = CanvasRenderingContext2D.prototype.getImageData;

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

  Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
    "value": function () {
      let result = rawGetContext.apply(this, arguments);
      if (arguments[0] === '2d') {
        ctxArr.push(result);
        ctxInf.push({});
      }
      return result;
    }, configurable: true
  });

  Object.defineProperty(HTMLCanvasElement.prototype.constructor, "length", {
    "value": 1, configurable: true, writable: true
  });

  Object.defineProperty(HTMLCanvasElement.prototype.constructor, "toString", {
    "value": () => "function getContext() { [native code] }", configurable: true, writable: true
  });

  Object.defineProperty(CanvasRenderingContext2D.prototype.constructor, "name", {
    "value": "getContext", configurable: true
  });

  let rawArc = CanvasRenderingContext2D.prototype.arc;
  Object.defineProperty(CanvasRenderingContext2D.prototype, "arc", {
    "value": function () {
      let ctxIdx = ctxArr.indexOf(this);
      ctxInf[ctxIdx].useArc = true;
      return rawArc.apply(this, arguments);
    }, configurable: true, writable: true
  });

  Object.defineProperty(CanvasRenderingContext2D.prototype.arc, "length", {
    "value": 5, configurable: true, writable: true
  });

  Object.defineProperty(CanvasRenderingContext2D.prototype.arc, "toString", {
    "value": () => "function arc() { [native code] }", configurable: true, writable: true
  });

  Object.defineProperty(CanvasRenderingContext2D.prototype.arc, "name", {
    "value": "arc", configurable: true, writable: true
  });

  const rawFillText = CanvasRenderingContext2D.prototype.fillText;
  Object.defineProperty(CanvasRenderingContext2D.prototype, "fillText", {
    "value": function () {
      let ctxIdx = ctxArr.indexOf(this);
      ctxInf[ctxIdx].useFillText = true;
      return rawFillText.apply(this, arguments);
    }, configurable: true, writable: true
  });

  Object.defineProperty(CanvasRenderingContext2D.prototype.fillText, "length", {
    "value": 4, configurable: true, writable: true
  });

  Object.defineProperty(CanvasRenderingContext2D.prototype.fillText, "toString", {
    "value": () => "function fillText() { [native code] }", configurable: true, writable: true
  });

  Object.defineProperty(CanvasRenderingContext2D.prototype.fillText, "name", {
    "value": "fillText", configurable: true, writable: true
  });

  // toBlob override
  Object.defineProperty(HTMLCanvasElement.prototype, "toBlob", {
    "value": function () {
      noisify(this, this.getContext("2d"));
      return toBlob.apply(this, arguments);
    }, configurable: true, writable: true
  });
  Object.defineProperty(HTMLCanvasElement.prototype.toBlob, "length", {
    "value": 1, configurable: true, writable: true
  });
  Object.defineProperty(HTMLCanvasElement.prototype.toBlob, "toString", {
    "value": () => "function toBlob() { [native code] }", configurable: true, writable: true
  });
  Object.defineProperty(HTMLCanvasElement.prototype.toBlob, "name", {
    "value": "toBlob", configurable: true, writable: true
  });

  // toDataURL override
  Object.defineProperty(HTMLCanvasElement.prototype, "toDataURL", {
    "value": function () {
      noisify(this, this.getContext("2d"));
      return toDataURL.apply(this, arguments);
    }, configurable: true, writable: true
  });
  Object.defineProperty(HTMLCanvasElement.prototype.toDataURL, "length", {
    "value": 0, configurable: true, writable: true
  });
  Object.defineProperty(HTMLCanvasElement.prototype.toDataURL, "toString", {
    "value": () => "function toDataURL() { [native code] }", configurable: true, writable: true
  });
  Object.defineProperty(HTMLCanvasElement.prototype.toDataURL, "name", {
    "value": "toDataURL", configurable: true, writable: true
  });

  // getImageData override
  Object.defineProperty(CanvasRenderingContext2D.prototype, "getImageData", {
    "value": function () {
      noisify(this.canvas, this);
      return getImageData.apply(this, arguments);
    }, configurable: true, writable: true
  });
  Object.defineProperty(CanvasRenderingContext2D.prototype.getImageData, "length", {
    "value": 4, configurable: true, writable: true
  });
  Object.defineProperty(CanvasRenderingContext2D.prototype.getImageData, "toString", {
    "value": () => "function getImageData() { [native code] }", configurable: true, writable: true
  });
  Object.defineProperty(CanvasRenderingContext2D.prototype.getImageData, "name", {
    "value": "getImageData", configurable: true, writable: true
  });
})();
