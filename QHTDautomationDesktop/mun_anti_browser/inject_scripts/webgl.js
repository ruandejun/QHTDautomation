// MunAntiBrowser - WebGL Fingerprint Spoof
// Modifies WebGL parameters to prevent GPU fingerprinting.
// Templates: {{gl_index}}, {{gl_noise}}, {{3412}}, {{37445}}, {{37446}}, {{7938}}, {{35724}},
//   {{3379}}, {{36347}}, {{34076}}, {{34024}}, {{3386}}, {{3413}}, {{3411}}, {{3410}},
//   {{34047}}, {{34930}}, {{34921}}, {{34324}}, {{35376}}, {{35377}}, {{35379}},
//   {{35658}}, {{35660}}, {{35661}}, {{36349}}, {{33902}}, {{33901}}

(function fakeWebgl() {
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
    },
    "spoof": {
      "webgl": {
        "buffer": function (target) {
          var proto = target.prototype ? target.prototype : target.__proto__;
          const bufferData = proto.bufferData;
          Object.defineProperty(proto, "bufferData", {
            "value": function () {
              var index = Math.floor({{gl_index}} * arguments[1].length);
              var noise = arguments[1][index] !== undefined ? 0.1 * {{gl_noise}} * arguments[1][index] : 0;
              arguments[1][index] = arguments[1][index] + noise;
              return bufferData.apply(this, arguments);
            }, configurable: true, writable: true
          });
        },
        "parameter": function (target) {
          var proto = target.prototype ? target.prototype : target.__proto__;
          const getParameter = proto.getParameter;
          Object.defineProperty(proto, "getParameter", {
            "value": function () {
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
              return getParameter.apply(this, arguments);
            }, configurable: true, writable: true
          });
        }
      }
    }
  };

  config.spoof.webgl.buffer(WebGLRenderingContext);
  config.spoof.webgl.buffer(WebGL2RenderingContext);
  config.spoof.webgl.parameter(WebGLRenderingContext);
  config.spoof.webgl.parameter(WebGL2RenderingContext);

  // ─── WebGL Rendering Fingerprint Noise ─────────────────────────
  // Hook readPixels to inject subtle pixel noise that changes the
  // WebGL rendering hash. Without this, the hash is determined
  // entirely by the real GPU hardware.
  var glNoiseSeed = {{gl_noise}} || 0.5;
  var glIndexSeed = {{gl_index}} || 0.3;

  // Better seed mixing to avoid collisions between profiles
  var _noiseSeed = (Math.floor(glNoiseSeed * 2147483647) * 7 + Math.floor(glIndexSeed * 2147483647) * 13) & 0x7FFFFFFF;
  if (_noiseSeed === 0) _noiseSeed = 1;
  function nextNoiseVal() {
    _noiseSeed = (_noiseSeed * 1103515245 + 12345) & 0x7FFFFFFF;
    return (_noiseSeed >> 16) & 0xFF;
  }

  function applyWebGLPixelNoise(pixels) {
    if (!pixels || !pixels.length) return;
    // Reset seed for deterministic output
    _noiseSeed = (Math.floor(glNoiseSeed * 2147483647) * 7 + Math.floor(glIndexSeed * 2147483647) * 13) & 0x7FFFFFFF;
    if (_noiseSeed === 0) _noiseSeed = 1;
    // Apply noise to R channel of every Nth pixel
    // We modify enough pixels to change the hash but keep it visually subtle
    var pixelCount = pixels.length / 4;
    var noiseEvery = Math.max(1, Math.floor(pixelCount / 200)); // ~200 pixels get noise
    for (var p = 0; p < pixelCount; p += noiseEvery) {
      var n = nextNoiseVal();
      var shift = (n % 7) - 3; // -3 to +3
      if (shift === 0) shift = (n & 1) ? 1 : -1;
      var idx = p * 4; // R channel
      var val = pixels[idx] + shift;
      pixels[idx] = val < 0 ? 0 : (val > 255 ? 255 : val);
      // Also slightly shift G channel for more uniqueness
      var n2 = nextNoiseVal();
      var shift2 = (n2 % 5) - 2; // -2 to +2
      pixels[idx + 1] = Math.max(0, Math.min(255, pixels[idx + 1] + shift2));
    }
  }

  // Hook readPixels on WebGLRenderingContext
  function hookReadPixels(proto) {
    var origReadPixels = proto.readPixels;
    if (!origReadPixels) return;
    Object.defineProperty(proto, 'readPixels', {
      value: function() {
        origReadPixels.apply(this, arguments);
        // arguments[6] is the pixels array (Uint8Array/Float32Array)
        var pixels = arguments[6];
        if (pixels && pixels.length) {
          applyWebGLPixelNoise(pixels);
        }
      },
      configurable: true,
      writable: true
    });
  }

  // Store original readPixels BEFORE our hook replaces them
  // (used by createNoisedWebGLCanvas to get clean pixel data)
  WebGLRenderingContext.prototype.__origReadPixels = WebGLRenderingContext.prototype.readPixels;
  WebGL2RenderingContext.prototype.__origReadPixels = WebGL2RenderingContext.prototype.readPixels;

  hookReadPixels(WebGLRenderingContext.prototype);
  hookReadPixels(WebGL2RenderingContext.prototype);

  // Hook toDataURL on canvases that use WebGL context
  // The canvas.js noisify() only handles 2D context, so WebGL canvases
  // are unaffected. We need to inject noise for WebGL canvas exports too.
  var _webglCanvases = new WeakMap(); // canvas -> gl context

  // Track which canvases have a WebGL context
  // Note: canvas.js may have already wrapped getContext. We chain on top.
  var currentGetContext = HTMLCanvasElement.prototype.getContext;
  Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
    value: function() {
      var result = currentGetContext.apply(this, arguments);
      var type = arguments[0];
      if (type === 'webgl' || type === 'webgl2' ||
          type === 'experimental-webgl') {
        _webglCanvases.set(this, result);
      }
      return result;
    },
    configurable: true,
    writable: true
  });

  // Helper: create a temp 2D canvas with noised WebGL pixels
  function createNoisedWebGLCanvas(canvas) {
    var gl = _webglCanvases.get(canvas);
    if (!gl) return null;
    try {
      var w = canvas.width, h = canvas.height;
      if (!w || !h) return null;
      var pixels = new Uint8Array(w * h * 4);
      // Use the ORIGINAL readPixels to get clean data, then apply noise manually
      var origRP = WebGLRenderingContext.prototype.__origReadPixels || WebGL2RenderingContext.prototype.__origReadPixels;
      if (origRP) {
        origRP.call(gl, 0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      } else {
        gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      }
      // Apply noise to the pixel data
      applyWebGLPixelNoise(pixels);
      // Create a 2D canvas with the noised pixels
      var tempCanvas = document.createElement('canvas');
      tempCanvas.width = w;
      tempCanvas.height = h;
      var ctx = tempCanvas.getContext('2d');
      var imageData = ctx.createImageData(w, h);
      // WebGL readPixels returns bottom-up, need to flip vertically
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

  // (__origReadPixels already stored before hookReadPixels above)

  // Wrap toDataURL to produce noised output for WebGL canvases
  var currentToDataURL = HTMLCanvasElement.prototype.toDataURL;
  Object.defineProperty(HTMLCanvasElement.prototype, 'toDataURL', {
    value: function() {
      if (_webglCanvases.has(this)) {
        var noised = createNoisedWebGLCanvas(this);
        if (noised) {
          return currentToDataURL.apply(noised, arguments);
        }
      }
      return currentToDataURL.apply(this, arguments);
    },
    configurable: true,
    writable: true
  });

  // Similarly wrap toBlob for WebGL canvases
  var currentToBlob = HTMLCanvasElement.prototype.toBlob;
  Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', {
    value: function() {
      if (_webglCanvases.has(this)) {
        var noised = createNoisedWebGLCanvas(this);
        if (noised) {
          return currentToBlob.apply(noised, arguments);
        }
      }
      return currentToBlob.apply(this, arguments);
    },
    configurable: true,
    writable: true
  });
})();
