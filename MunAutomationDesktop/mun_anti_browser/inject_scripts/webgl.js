// MunAntiBrowser - WebGL Fingerprint Spoof
// Modifies WebGL parameters to prevent GPU fingerprinting.
// Templates: {{gl_index}}, {{gl_noise}}, {{3412}}, {{37445}}, {{37446}}, {{7938}}, {{35724}},
//   {{3379}}, {{36347}}, {{34076}}, {{34024}}, {{3386}}, {{3413}}, {{3411}}, {{3410}},
//   {{34047}}, {{34930}}, {{34921}}, {{34324}}, {{35376}}, {{35377}}, {{35379}},
//   {{35658}}, {{35660}}, {{35661}}, {{36349}}, {{33902}}, {{33901}}

(function fakeWebgl() {
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

  var config = {
    "random": {
      "value": function () {
        return Math.random();
      },
      "item": function (e) {
        var rand = e.length * config.random.value();
        return e[Math.floor(rand)];
      },
      "number": function (power) {
        var tmp = [];
        for (var i = 0; i < power.length; i++) {
          tmp.push(Math.pow(2, power[i]));
        }
        return config.random.item(tmp);
      },
      "int": function (power) {
        var tmp = [];
        for (var i = 0; i < power.length; i++) {
          var n = Math.pow(2, power[i]);
          tmp.push(new Int32Array([n, n]));
        }
        return config.random.item(tmp);
      },
      "float": function (power) {
        var tmp = [];
        for (var i = 0; i < power.length; i++) {
          var n = Math.pow(2, power[i]);
          tmp.push(new Float32Array([1, n]));
        }
        return config.random.item(tmp);
      }
    }
  };

  // ─── WebGL Rendering Fingerprint Noise ─────────────────────────
  var glNoiseSeed = {{gl_noise}} || 0.5;
  var glIndexSeed = {{gl_index}} || 0.3;

  var _noiseSeed = (Math.floor(glNoiseSeed * 2147483647) * 7 + Math.floor(glIndexSeed * 2147483647) * 13) & 0x7FFFFFFF;
  if (_noiseSeed === 0) _noiseSeed = 1;
  function nextNoiseVal() {
    _noiseSeed = (_noiseSeed * 1103515245 + 12345) & 0x7FFFFFFF;
    return (_noiseSeed >> 16) & 0xFF;
  }

  function applyWebGLPixelNoise(pixels) {
    if (!pixels || !pixels.length) return;
    _noiseSeed = (Math.floor(glNoiseSeed * 2147483647) * 7 + Math.floor(glIndexSeed * 2147483647) * 13) & 0x7FFFFFFF;
    if (_noiseSeed === 0) _noiseSeed = 1;
    var pixelCount = pixels.length / 4;
    var noiseEvery = Math.max(1, Math.floor(pixelCount / 200));
    for (var p = 0; p < pixelCount; p += noiseEvery) {
      var n = nextNoiseVal();
      var shift = (n % 7) - 3;
      if (shift === 0) shift = (n & 1) ? 1 : -1;
      var idx = p * 4;
      var val = pixels[idx] + shift;
      pixels[idx] = val < 0 ? 0 : (val > 255 ? 255 : val);
      var n2 = nextNoiseVal();
      var shift2 = (n2 % 5) - 2;
      pixels[idx + 1] = Math.max(0, Math.min(255, pixels[idx + 1] + shift2));
    }
  }

  // 1. Hook bufferData
  const rawBufferData = WebGLRenderingContext.prototype.bufferData;
  const rawBufferData2 = WebGL2RenderingContext.prototype.bufferData;

  const wrappedBufferData = function () {
    if (arguments[1] && arguments[1].length) {
      var index = Math.floor({{gl_index}} * arguments[1].length);
      var noise = arguments[1][index] !== undefined ? 0.1 * {{gl_noise}} * arguments[1][index] : 0;
      arguments[1][index] = arguments[1][index] + noise;
    }
    return rawBufferData.apply(this, arguments);
  };
  
  const wrappedBufferData2 = function () {
    if (arguments[1] && arguments[1].length) {
      var index = Math.floor({{gl_index}} * arguments[1].length);
      var noise = arguments[1][index] !== undefined ? 0.1 * {{gl_noise}} * arguments[1][index] : 0;
      arguments[1][index] = arguments[1][index] + noise;
    }
    return rawBufferData2.apply(this, arguments);
  };

  patchMethod(WebGLRenderingContext.prototype, "bufferData", wrappedBufferData, rawBufferData.length);
  patchMethod(WebGL2RenderingContext.prototype, "bufferData", wrappedBufferData2, rawBufferData2.length);

  // 2. Hook getParameter
  const rawGetParameter = WebGLRenderingContext.prototype.getParameter;
  const rawGetParameter2 = WebGL2RenderingContext.prototype.getParameter;

  const getParameterFake = function (origFunc) {
    return function () {
      if (arguments[0] === 3415) return {{3412}};
      else if (arguments[0] === 3414) return {{3412}};
      else if (arguments[0] === 35375) return {{3412}};
      else if (arguments[0] === 35374) return {{3412}};
      else if (arguments[0] === 35380) return {{3412}};
      else if (arguments[0] === 34045) return {{3412}};
      else if (arguments[0] === 36348) return {{3412}};
      else if (arguments[0] === 35371) return {{3412}};
      else if (arguments[0] === 37154) return {{3412}};
      else if (arguments[0] === 35659) return {{3412}};
      else if (arguments[0] === 35978) return {{3412}};
      else if (arguments[0] === 35979) return {{3412}};
      else if (arguments[0] === 35968) return {{3412}};
      else if (arguments[0] === 34852) return {{3412}};
      else if (arguments[0] === 36063) return {{3412}};
      else if (arguments[0] === 36183) return {{3412}};
      else if (arguments[0] === 7936) return "WebKit";
      else if (arguments[0] === 37445) return "{{37445}}";
      else if (arguments[0] === 7937) return "WebKit WebGL";
      else if (arguments[0] === 3379) return {{3379}};
      else if (arguments[0] === 36347) return {{36347}};
      else if (arguments[0] === 34076) return {{34076}};
      else if (arguments[0] === 34024) return {{34024}};
      else if (arguments[0] === 3386) return {{3386}};
      else if (arguments[0] === 3413) return {{3413}};
      else if (arguments[0] === 3412) return {{3412}};
      else if (arguments[0] === 3411) return {{3411}};
      else if (arguments[0] === 3410) return {{3410}};
      else if (arguments[0] === 34047) return {{34047}};
      else if (arguments[0] === 34930) return {{34930}};
      else if (arguments[0] === 34921) return {{34921}};
      else if (arguments[0] === 34324) return Math.floor({{34324}} * 6100) + 8192;
      else if (arguments[0] === 35376) return Math.floor({{35376}} * 36384) + 10384;
      else if (arguments[0] === 35377) return Math.floor({{35377}} * 50188) + 20188;
      else if (arguments[0] === 35379) return Math.floor({{35379}} * 50188) + 20188;
      else if (arguments[0] === 35658) return Math.floor({{35658}} * 36) + 1000;
      else if (arguments[0] === 35660) return {{35660}};
      else if (arguments[0] === 35661) return {{35661}};
      else if (arguments[0] === 36349) return {{36349}};
      else if (arguments[0] === 33902) return {{33902}};
      else if (arguments[0] === 33901) return {{33901}};
      else if (arguments[0] === 37446) return "{{37446}}";
      else if (arguments[0] === 7938) return "{{7938}}";
      else if (arguments[0] === 35724) return "{{35724}}";
      return origFunc.apply(this, arguments);
    };
  };

  const wrappedGetParameter = getParameterFake(rawGetParameter);
  const wrappedGetParameter2 = getParameterFake(rawGetParameter2);

  patchMethod(WebGLRenderingContext.prototype, "getParameter", wrappedGetParameter, rawGetParameter.length);
  patchMethod(WebGL2RenderingContext.prototype, "getParameter", wrappedGetParameter2, rawGetParameter2.length);

  // 3. Hook readPixels
  const rawReadPixels = WebGLRenderingContext.prototype.readPixels;
  const rawReadPixels2 = WebGL2RenderingContext.prototype.readPixels;

  const wrappedReadPixels = function() {
    rawReadPixels.apply(this, arguments);
    var pixels = arguments[6];
    if (pixels && pixels.length) {
      applyWebGLPixelNoise(pixels);
    }
  };

  const wrappedReadPixels2 = function() {
    rawReadPixels2.apply(this, arguments);
    var pixels = arguments[6];
    if (pixels && pixels.length) {
      applyWebGLPixelNoise(pixels);
    }
  };

  WebGLRenderingContext.prototype.__origReadPixels = rawReadPixels;
  WebGL2RenderingContext.prototype.__origReadPixels = rawReadPixels2;

  patchMethod(WebGLRenderingContext.prototype, 'readPixels', wrappedReadPixels, rawReadPixels.length);
  patchMethod(WebGL2RenderingContext.prototype, 'readPixels', wrappedReadPixels2, rawReadPixels2.length);

  // 4. Canvas overrides for WebGL dataURL/blob exports
  var _webglCanvases = new WeakMap();

  const rawGetContext = HTMLCanvasElement.prototype.getContext;
  const wrappedGetContext = function() {
    var result = rawGetContext.apply(this, arguments);
    var type = arguments[0];
    if (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl') {
      _webglCanvases.set(this, result);
    }
    return result;
  };
  patchMethod(HTMLCanvasElement.prototype, 'getContext', wrappedGetContext, rawGetContext.length);

  function createNoisedWebGLCanvas(canvas) {
    var gl = _webglCanvases.get(canvas);
    if (!gl) return null;
    try {
      var w = canvas.width, h = canvas.height;
      if (!w || !h) return null;
      var pixels = new Uint8Array(w * h * 4);
      var origRP = WebGLRenderingContext.prototype.__origReadPixels || WebGL2RenderingContext.prototype.__origReadPixels;
      if (origRP) {
        origRP.call(gl, 0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      } else {
        gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      }
      applyWebGLPixelNoise(pixels);
      var tempCanvas = document.createElement('canvas');
      tempCanvas.width = w;
      tempCanvas.height = h;
      var ctx = tempCanvas.getContext('2d');
      var imageData = ctx.createImageData(w, h);
      for (var row = 0; row < h; row++) {
        var srcRow = (h - 1 - row) * w * 4;
        var dstRow = row * w * 4;
        for (var col = 0; col < w * 4; col++) {
          imageData.data[dstRow + col] = pixels[srcRow + col];
        }
      }
      ctx.putImageData(imageData, 0, 0);
      return tempCanvas;
    } catch (e) {
      return null;
    }
  }

  const rawToDataURL = HTMLCanvasElement.prototype.toDataURL;
  const wrappedToDataURL = function() {
    if (_webglCanvases.has(this)) {
      var noised = createNoisedWebGLCanvas(this);
      if (noised) {
        return rawToDataURL.apply(noised, arguments);
      }
    }
    return rawToDataURL.apply(this, arguments);
  };
  patchMethod(HTMLCanvasElement.prototype, 'toDataURL', wrappedToDataURL, rawToDataURL.length);

  const rawToBlob = HTMLCanvasElement.prototype.toBlob;
  const wrappedToBlob = function() {
    if (_webglCanvases.has(this)) {
      var noised = createNoisedWebGLCanvas(this);
      if (noised) {
        return rawToBlob.apply(noised, arguments);
      }
    }
    return rawToBlob.apply(this, arguments);
  };
  patchMethod(HTMLCanvasElement.prototype, 'toBlob', wrappedToBlob, rawToBlob.length);
})();
