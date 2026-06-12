from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from selenium import webdriver

import time, random
from user_agents import parse
import math
def BrowserSelenium():      
    canvas_js = '''
      (function FakeNetwork() {
        var nothingtest = 1;
        var nothingtest2 = 1; 
        function processFunctions(scope) {
          var nothingtest3 = 1;
          nothingtest = nothingtest + 1;
          nothingtest2 = nothingtest2 + 1;
          nothingtest3 = nothingtest3 + 1;
        if (nothingtest2 < 3000) {
          scope.Object.defineProperty(navigator.connection, "downlink", {enumerable: true, configurable: true, get: function() {
            return [4.9,4.9,4.05,7.15,6.15,8.15,4.15,6.15,5.15,4.9,4.9,4.9,4.9,4.9,4.9,4.9,5,5,8.05,3.3,3.9,4.9,5.15,5.4,5.15,4.15,7.1,7.15,7.3,8,8.15,4.55,6.5,6.95,6.2,4.15][Math.floor(Math.random() * 36)];
          }});
            scope.Object.defineProperty(navigator.connection, "effectiveType", {enumerable: true, configurable: true, get: function() {
            return '4g';
          }});
            scope.Object.defineProperty(navigator.connection, "rtt", {enumerable: true, configurable: true, get: function() {
            return [50,150,100,100,150,150,150,150,100,100,100,100,100,150,150][Math.floor(Math.random() * 15)];
          }});
            scope.Object.defineProperty(navigator.connection, "saveData", {enumerable: true, configurable: true, get: function() {
            return false;
          }});
              
          } else {
          }				
        }
        processFunctions(window);
          var iwin = HTMLIFrameElement.prototype.__lookupGetter__('contentWindow'), idoc = HTMLIFrameElement.prototype.__lookupGetter__('contentDocument');
          Object.defineProperties(HTMLIFrameElement.prototype, {
            contentWindow: {
              get: function() {
                var frame = iwin.apply(this);
                if (this.src && this.src.indexOf('//') != -1 && location.host != this.src.split('/')[2]) return frame;
                try { frame.HTMLCanvasElement } catch (err) { /* do nothing*/ }
                try { processFunctions(frame); } catch (err) { /* do nothing*/ }
                return frame;
              }
            },
            contentDocument: {
              get: function() {
                if (this.src && this.src.indexOf('//') != -1 && location.host != this.src.split('/')[2]) return idoc.apply(this);
                var frame = iwin.apply(this);
                try { frame.HTMLCanvasElement } catch (err) { /* do nothing*/ }
                processFunctions(frame);
                return idoc.apply(this);
              }
            }
        });
        console.log('==fakeNetwork==');  
      }());
    (function fakeClientRects() {
      var _nativegetClientRects = Element.prototype.getClientRects; 
      Element.prototype['getClientRects'] = function() { 
      return [{
              'top': 0,
              'bottom': 0,
              'left': 0,
              'right': 0,
              'height': 0,
              'width': 0
          }];
      };
      console.log('==fakeClientRects==');     
    })();
    (function fakeWebglFingerPrint() {
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
            /*  */
            return config.random.item(tmp);
          },
          "int": function (power) {
            var tmp = [];
            for (var i = 0; i < power.length; i++) {
              var n = Math.pow(2, power[i]);
              tmp.push(new Int32Array([n, n]));
            }
            /*  */
            return config.random.item(tmp);
          },
          "float": function (power) {
            var tmp = [];
            for (var i = 0; i < power.length; i++) {
              var n = Math.pow(2, power[i]);
              tmp.push(new Float32Array([1, n]));
            }
            /*  */
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
                  //
                  arguments[1][index] = arguments[1][index] + noise;
                  //
                  return bufferData.apply(this, arguments);
                }
              });
            },
            "parameter": function (target) {
              var proto = target.prototype ? target.prototype : target.__proto__;
              const getParameter = proto.getParameter;
              Object.defineProperty(proto, "getParameter", {
                "value": function () {
                  //window.top.postMessage("webgl-fingerprint-defender-alert", '*');
                  //
                  if (arguments[0] === 3415) return 0;
                  else if (arguments[0] === 3414) return 24;
                  else if (arguments[0] === 3410) return 8;
                  else if (arguments[0] === 3411) return 8;
                  else if (arguments[0] === 3412) return 8;
                  else if (arguments[0] === 3413) return 8;
                  else if (arguments[0] === 3415) return 8;
                  else if (arguments[0] === 35375) return 24;
                  else if (arguments[0] === 35374) return 24;
                  else if (arguments[0] === 35380) return 4;
                  else if (arguments[0] === 34045) return 12;
                  else if (arguments[0] === 36348) return 32;
                  else if (arguments[0] === 35371) return 12;
                  else if (arguments[0] === 37154) return 64;
                  else if (arguments[0] === 35659) return 128;
                  else if (arguments[0] === 35978) return 64;
                  else if (arguments[0] === 35979) return 4;
                  else if (arguments[0] === 35968) return 64;
                  else if (arguments[0] === 34852) return 8;
                  else if (arguments[0] === 36063) return 8;
                  else if (arguments[0] === 36183) return 4;
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
                  //
                  return getParameter.apply(this, arguments);
                }
              });
            }
          }
        }
      };  
      config.spoof.webgl.buffer(WebGLRenderingContext);
      config.spoof.webgl.buffer(WebGL2RenderingContext);
      config.spoof.webgl.parameter(WebGLRenderingContext);
      config.spoof.webgl.parameter(WebGL2RenderingContext);
      console.log('==fakeWebglFingerPrint==');
    })();       
    (function fakeCanvasFingerPrint() {
        const toBlob = HTMLCanvasElement.prototype.toBlob;
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        const getImageData = CanvasRenderingContext2D.prototype.getImageData;
        //
        var noisify = function (canvas, context) {
            //console.log('==let noisify==',context);
            if (context) {
              const shift = {{canvas_shift}};
              //
              let ctxIdx = ctxArr.indexOf(context);
              let info = ctxInf[ctxIdx];
              const width = canvas.width;
              const height = canvas.height;
              if (info.useArc || info.useFillText && width && height) {
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
                //
                //window.top.postMessage("canvas-fingerprint-defender-alert", '*');
                context.putImageData(imageData, 0, 0); 
              }
            }
        };
        let ctxArr = [];
        let ctxInf = [];    
        let rawGetContext = HTMLCanvasElement.prototype.getContext
     
        Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
            "value": function () {
                let result = rawGetContext.apply(this, arguments);
                if (arguments[0] === '2d') {
                    ctxArr.push(result)
                    ctxInf.push({})
                }
                return result;
            }
        });
     
        Object.defineProperty(HTMLCanvasElement.prototype.constructor, "length", {
            "value": 1
        });
     
        Object.defineProperty(HTMLCanvasElement.prototype.constructor, "toString", {
            "value": () => "function getContext() { [native code] }"
        });
     
        Object.defineProperty(CanvasRenderingContext2D.prototype.constructor, "name", {
            "value": "getContext"
        });
        let rawArc = CanvasRenderingContext2D.prototype.arc
        Object.defineProperty(CanvasRenderingContext2D.prototype, "arc", {
            "value": function () {
                let ctxIdx = ctxArr.indexOf(this);
                ctxInf[ctxIdx].useArc = true;
                return rawArc.apply(this, arguments);
            }
        });
     
        Object.defineProperty(CanvasRenderingContext2D.prototype.arc, "length", {
            "value": 5
        });
     
        Object.defineProperty(CanvasRenderingContext2D.prototype.arc, "toString", {
            "value": () => "function arc() { [native code] }"
        });
     
        Object.defineProperty(CanvasRenderingContext2D.prototype.arc, "name", {
            "value": "arc"
        });    
        const rawFillText = CanvasRenderingContext2D.prototype.fillText;
        Object.defineProperty(CanvasRenderingContext2D.prototype, "fillText", {
            "value": function () {
                let ctxIdx = ctxArr.indexOf(this);
                ctxInf[ctxIdx].useFillText = true;
                return rawFillText.apply(this, arguments);
            }
        });
     
        Object.defineProperty(CanvasRenderingContext2D.prototype.fillText, "length", {
            "value": 4
        });
     
        Object.defineProperty(CanvasRenderingContext2D.prototype.fillText, "toString", {
            "value": () => "function fillText() { [native code] }"
        });
     
        Object.defineProperty(CanvasRenderingContext2D.prototype.fillText, "name", {
            "value": "fillText"
        }); 
        //
        Object.defineProperty(HTMLCanvasElement.prototype, "toBlob", {
            "value": function () {
              noisify(this, this.getContext("2d"));
              return toBlob.apply(this, arguments);
            }
        });
        Object.defineProperty(HTMLCanvasElement.prototype.toBlob, "length", {
            "value": 1
        });
     
        Object.defineProperty(HTMLCanvasElement.prototype.toBlob, "toString", {
            "value": () => "function toBlob() { [native code] }"
        });
     
        Object.defineProperty(HTMLCanvasElement.prototype.toBlob, "name", {
            "value": "toBlob"
        });  
        //
        Object.defineProperty(HTMLCanvasElement.prototype, "toDataURL", {
            "value": function () {
              noisify(this, this.getContext("2d"));
              return toDataURL.apply(this, arguments);
            }
        });
        Object.defineProperty(HTMLCanvasElement.prototype.toDataURL, "length", {
            "value": 0
        });
     
        Object.defineProperty(HTMLCanvasElement.prototype.toDataURL, "toString", {
            "value": () => "function toDataURL() { [native code] }"
        });
     
        Object.defineProperty(HTMLCanvasElement.prototype.toDataURL, "name", {
            "value": "toDataURL"
        });
        //
        Object.defineProperty(CanvasRenderingContext2D.prototype, "getImageData", {
            "value": function () {
              noisify(this.canvas, this);
              return getImageData.apply(this, arguments);
            }
        });
        Object.defineProperty(CanvasRenderingContext2D.prototype.getImageData, "length", {
            "value": 4
        });
     
        Object.defineProperty(CanvasRenderingContext2D.prototype.getImageData, "toString", {
            "value": () => "function getImageData() { [native code] }"
        });
     
        Object.defineProperty(CanvasRenderingContext2D.prototype.getImageData, "name", {
            "value": "getImageData"
        });
    })();


    (function fakeAudioFinger() {
      const context = {
        "BUFFER": null,
        "getChannelData": function (e) {
          const getChannelData = e.prototype.getChannelData;
          Object.defineProperty(e.prototype, "getChannelData", {
            "value": function () {
              const results_1 = getChannelData.apply(this, arguments);
              if (context.BUFFER !== results_1) {
                context.BUFFER = results_1;
   
                let obj2 = {{audio_content}};
                for (const key of Object.keys(obj2)) {
                    results_1[key] = obj2[key]
                }
              }
              return results_1;
            }
          });
        },
        "createAnalyser": function (e) {
          const createAnalyser = e.prototype.__proto__.createAnalyser;
          Object.defineProperty(e.prototype.__proto__, "createAnalyser", {
            "value": function () {
              const results_2 = createAnalyser.apply(this, arguments);
              const getFloatFrequencyData = results_2.__proto__.getFloatFrequencyData;
              Object.defineProperty(results_2.__proto__, "getFloatFrequencyData", {
                "value": function () {
                  const results_3 = getFloatFrequencyData.apply(this, arguments);
                  for (var i = 0; i < arguments[0].length; i += 100) {
                    let index = Math.floor({{audio_random1}} * i);
                    var new_value = arguments[0][index] + {{audio_random2}} * 0.1;
                    arguments[0][index] = new_value
                  }
                  return results_3;
                }
              });
              //
              return results_2;
            }
          });
        }
      };
      //
      context.getChannelData(AudioBuffer);
      context.createAnalyser(AudioContext);
      context.getChannelData(OfflineAudioContext);
      context.createAnalyser(OfflineAudioContext);
      console.log('==fakeAudioFinger==',AudioBuffer);
    })();

    const iframes = [...window.top.document.querySelectorAll("iframe[sandbox]")];
    for (var i = 0; i < iframes.length; i++) {
      if (iframes[i].contentWindow) {
        if (iframes[i].contentWindow.AudioBuffer) {
          if (iframes[i].contentWindow.AudioBuffer.prototype) {
            if (iframes[i].contentWindow.AudioBuffer.prototype.getChannelData) {
              iframes[i].contentWindow.AudioBuffer.prototype.getChannelData = AudioBuffer.prototype.getChannelData;
            }
          }
        }

        if (iframes[i].contentWindow.AudioContext) {
          if (iframes[i].contentWindow.AudioContext.prototype) {
            if (iframes[i].contentWindow.AudioContext.prototype.__proto__) {
              if (iframes[i].contentWindow.AudioContext.prototype.__proto__.createAnalyser) {
                iframes[i].contentWindow.AudioContext.prototype.__proto__.createAnalyser = AudioContext.prototype.__proto__.createAnalyser;
              }
            }
          }
        }

        if (iframes[i].contentWindow.OfflineAudioContext) {
          if (iframes[i].contentWindow.OfflineAudioContext.prototype) {
            if (iframes[i].contentWindow.OfflineAudioContext.prototype.__proto__) {
              if (iframes[i].contentWindow.OfflineAudioContext.prototype.__proto__.createAnalyser) {
                iframes[i].contentWindow.OfflineAudioContext.prototype.__proto__.createAnalyser = OfflineAudioContext.prototype.__proto__.createAnalyser;
              }
            }
          }
        }

        if (iframes[i].contentWindow.OfflineAudioContext) {
          if (iframes[i].contentWindow.OfflineAudioContext.prototype) {
            if (iframes[i].contentWindow.OfflineAudioContext.prototype.__proto__) {
              if (iframes[i].contentWindow.OfflineAudioContext.prototype.__proto__.getChannelData) {
                iframes[i].contentWindow.OfflineAudioContext.prototype.__proto__.getChannelData = OfflineAudioContext.prototype.__proto__.getChannelData;
              }
            }
          }
        }
      }
    }
    ( function fakeTimeZone() {
        Date.prefs = {{timeZoneArray}};
        console.log('==Date.prefs==',Date.prefs);
        const ODateTimeFormat = Intl.DateTimeFormat;
        Intl.DateTimeFormat = function(locales, options = {}) {
          Object.assign(options, {
            timeZone: Date.prefs[0]
          });
          return ODateTimeFormat(locales, options);
        };
        Intl.DateTimeFormat.prototype = Object.create(ODateTimeFormat.prototype);
        Intl.DateTimeFormat.supportedLocalesOf = ODateTimeFormat.supportedLocalesOf;
        const clean = str => {
          const toGMT = offset => {
            const z = n => (n < 10 ? '0' : '') + n;
            const sign = offset <= 0 ? '+' : '-';
            offset = Math.abs(offset);
            return sign + z(offset / 60 | 0) + z(offset % 60);
          };
          str = str.replace(/([T\\(])[\\+-]\\d+/g, '$1' + toGMT(Date.prefs[1]));
          if (str.indexOf(' (') !== -1) {
            str = str.split(' (')[0] + ' (' + Date.prefs[3] + ')';
          }
          return str;
        }

        const ODate = Date;
        const {
          getTime, getDate, getDay, getFullYear, getHours, getMilliseconds, getMinutes, getMonth, getSeconds, getYear,
          toDateString, toLocaleString, toString, toTimeString, toLocaleTimeString, toLocaleDateString,
          setYear, setHours, setTime, setFullYear, setMilliseconds, setMinutes, setMonth, setSeconds, setDate,
          setUTCDate, setUTCFullYear, setUTCHours, setUTCMilliseconds, setUTCMinutes, setUTCMonth, setUTCSeconds
        } = ODate.prototype;
        
        class ShiftedDate extends ODate {
          constructor(...args) {
            super(...args);
            this.nd = new ODate(
              getTime.apply(this) + (Date.prefs[2] - Date.prefs[1]) * 60 * 1000
            );
          }
          // get
          toLocaleString(...args) {
            return toLocaleString.apply(this.nd, args);
          }
          toLocaleTimeString(...args) {
            return toLocaleTimeString.apply(this.nd, args);
          }
          toLocaleDateString(...args) {
            return toLocaleDateString.apply(this.nd, args);
          }
          toDateString(...args) {
            return toDateString.apply(this.nd, args);
          }
          getDate(...args) {
            return getDate.apply(this.nd, args);
          }
          getDay(...args) {
            return getDay.apply(this.nd, args);
          }
          getFullYear(...args) {
            return getFullYear.apply(this.nd, args);
          }
          getHours(...args) {
            return getHours.apply(this.nd, args);
          }
          getMilliseconds(...args) {
            return getMilliseconds.apply(this.nd, args);
          }
          getMinutes(...args) {
            return getMinutes.apply(this.nd, args);
          }
          getMonth(...args) {
            return getMonth.apply(this.nd, args);
          }
          getSeconds(...args) {
            return getSeconds.apply(this.nd, args);
          }
          getYear(...args) {
            return getYear.apply(this.nd, args);
          }
          // set
          setHours(...args) {
            const a = getTime.call(this.nd);
            const b = setHours.apply(this.nd, args);
            setTime.call(this, getTime.call(this) + b - a);
            return b;
          }
          setFullYear(...args) {
            const a = getTime.call(this.nd);
            const b = setFullYear.apply(this.nd, args);
            setTime.call(this, getTime.call(this) + b - a);
            return b;
          }
          setMilliseconds(...args) {
            const a = getTime.call(this.nd);
            const b = setMilliseconds.apply(this.nd, args);
            setTime.call(this, getTime.call(this) + b - a);
            return b;
          }
          setMinutes(...args) {
            const a = getTime.call(this.nd);
            const b = setMinutes.apply(this.nd, args);
            setTime.call(this, getTime.call(this) + b - a);
            return b;
          }
          setMonth(...args) {
            const a = getTime.call(this.nd);
            const b = setMonth.apply(this.nd, args);
            setTime.call(this, getTime.call(this) + b - a);
            return b;
          }
          setSeconds(...args) {
            const a = getTime.call(this.nd);
            const b = setSeconds.apply(this.nd, args);
            setTime.call(this, getTime.call(this) + b - a);
            return b;
          }
          setDate(...args) {
            const a = getTime.call(this.nd);
            const b = setDate.apply(this.nd, args);
            setTime.call(this, getTime.call(this) + b - a);
            return b;
          }
          setYear(...args) {
            const a = getTime.call(this.nd);
            const b = setYear.apply(this.nd, args);
            setTime.call(this, getTime.call(this) + b - a);
            return b;
          }
          setTime(...args) {
            const a = getTime.call(this);
            const b = setTime.apply(this, args);
            setTime.call(this.nd, getTime.call(this.nd) + b - a);
            return b;
          }
          setUTCDate(...args) {
            const a = getTime.call(this);
            const b = setUTCDate.apply(this, args);
            setTime.call(this.nd, getTime.call(this.nd) + b - a);
            return b;
          }
          setUTCFullYear(...args) {
            const a = getTime.call(this);
            const b = setUTCFullYear.apply(this, args);
            setTime.call(this.nd, getTime.call(this.nd) + b - a);
            return b;
          }
          setUTCHours(...args) {
            const a = getTime.call(this);
            const b = setUTCHours.apply(this, args);
            setTime.call(this.nd, getTime.call(this.nd) + b - a);
            return b;
          }
          setUTCMilliseconds(...args) {
            const a = getTime.call(this);
            const b = setUTCMilliseconds.apply(this, args);
            setTime.call(this.nd, getTime.call(this.nd) + b - a);
            return b;
          }
          setUTCMinutes(...args) {
            const a = getTime.call(this);
            const b = setUTCMinutes.apply(this, args);
            setTime.call(this.nd, getTime.call(this.nd) + b - a);
            return b;
          }
          setUTCMonth(...args) {
            const a = getTime.call(this);
            const b = setUTCMonth.apply(this, args);
            setTime.call(this.nd, getTime.call(this.nd) + b - a);
            return b;
          }
          setUTCSeconds(...args) {
            const a = getTime.call(this);
            const b = setUTCSeconds.apply(this, args);
            setTime.call(this.nd, getTime.call(this.nd) + b - a);
            return b;
          }
          // toString
          toString(...args) {
            return clean(toString.apply(this.nd, args));
          }
          toTimeString(...args) {
            return clean(toTimeString.apply(this.nd, args));
          }
          // offset
          getTimezoneOffset() {
            return Date.prefs[1];
          }
        }
        Date = ShiftedDate;
        console.log('==fakeTimeZone==');       
    })();
    (function fakeFonts() {
      var rand = {
        "noise": function () {
          var SIGN = Math.random() < Math.random() ? -1 : 1;
          return Math.floor(Math.random() + SIGN * Math.random());
        },
        "sign": function () {
          const tmp = [-1, -1, -1, -1, -1, -1, +1, -1, -1, -1];
          const index = Math.floor(Math.random() * tmp.length);
          return tmp[index];
        }
      };
      //
      console.log('rand.sign()==',)
      Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
        get () {
          const height = Math.floor(this.getBoundingClientRect().height);
          const valid = height && rand.sign() === 1;
          const result = valid ? height + rand.noise() : height;
          //
          if (valid && result !== height) {
            window.top.postMessage("font-fingerprint-defender-alert", '*');
          }
          //
          return result;
        }
      });
      //
      Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
        get () {
          const width = Math.floor(this.getBoundingClientRect().width);
          const valid = width && rand.sign() === 1;
          const result = valid ? width + rand.noise() : width;

          return result;
        }
      });
      //
      console.log('==fakeFonts==');     
    })();    
    '''
  
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"#ua.random
    user_agent_info = parse(user_agent)
    print(user_agent)
    list_screen_size= [(1920,1080),(1366,768),(1280,1024),(1280,800),(1024,768)]
    screen_width, screen_height = list_screen_size[random.randint(0, len(list_screen_size) - 1)]
    
    options = webdriver.ChromeOptions()
    options.add_argument(f'user-agent={user_agent}')
    options.add_argument(f"--window-size={screen_width},{screen_height}")
    options.add_argument("--user-data-dir=/Users/test/Documents/antidetect-automatic/chrome data/ruandejun") 
    options.add_argument("--disable-blink-features")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("detach", True)
    options.add_experimental_option("prefs", {"enforce-webrtc-ip-permission-check": True 
      })
    options.add_argument("force-webrtc-ip-handling-policy")
    capabilities = webdriver.DesiredCapabilities.CHROME.copy()   
    driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(),desired_capabilities=capabilities, chrome_options=options)

    

    list_length = 44100
    listAudioContent = {}
    i=0
    while i < list_length:
        index = int(random.uniform(0.01, 0.99)*i)
        listAudioContent[index] = random.uniform(0.01, 0.99) * 0.0000001
        i+=100
    audio_random1 = random.uniform(0.01, 0.99)
    audio_random2 = random.uniform(0.01, 0.99)
    canvas_js = canvas_js.replace('{{audio_content}}',str(listAudioContent))
    canvas_js = canvas_js.replace('{{audio_random1}}',str(audio_random1))
    canvas_js = canvas_js.replace('{{audio_random2}}',str(audio_random2))
    print('listAudioContent==',len(listAudioContent))
    #random listcanvas    
    list_canvas = [-3,-2,-1,0,1,2,3]
    rsalt_content = list_canvas[random.randint(0, len(list_canvas) - 1)]
    gsalt_content = list_canvas[random.randint(0, len(list_canvas) - 1)]
    bsalt_content = list_canvas[random.randint(0, len(list_canvas) - 1)]
    asalt_content = list_canvas[random.randint(0, len(list_canvas) - 1)]
    canvas_shift = {'r': rsalt_content,'g': gsalt_content,'b': bsalt_content,'a': asalt_content}
    canvas_js = canvas_js.replace('{{canvas_shift}}', str(canvas_shift))


    ##timezone
    timezoneDict = {"Pacific/Niue":{"offset":-660,"msg":{"standard":"Niue Time"}},"Pacific/Pago_Pago":{"offset":-660},"Pacific/Honolulu":{"offset":-600},"Pacific/Rarotonga":{"offset":-600},"Pacific/Tahiti":{"offset":-600,"msg":{"standard":"Tahiti Time"}},"Pacific/Marquesas":{"offset":-510,"msg":{"standard":"Marquesas Time"}},"America/Anchorage":{"offset":-540},"Pacific/Gambier":{"offset":-540,"msg":{"standard":"Gambier Time"}},"America/Los_Angeles":{"offset":-480},"America/Tijuana":{"offset":-480},"America/Vancouver":{"offset":-480},"America/Whitehorse":{"offset":-480},"Pacific/Pitcairn":{"offset":-480,"msg":{"standard":"Pitcairn Time"}},"America/Dawson_Creek":{"offset":-420},"America/Denver":{"offset":-420},"America/Edmonton":{"offset":-420},"America/Hermosillo":{"offset":-420},"America/Mazatlan":{"offset":-420},"America/Phoenix":{"offset":-420},"America/Yellowknife":{"offset":-420},"America/Belize":{"offset":-360},"America/Chicago":{"offset":-360},"America/Costa_Rica":{"offset":-360},"America/El_Salvador":{"offset":-360},"America/Guatemala":{"offset":-360},"America/Managua":{"offset":-360},"America/Mexico_City":{"offset":-360},"America/Regina":{"offset":-360},"America/Tegucigalpa":{"offset":-360},"America/Winnipeg":{"offset":-360},"Pacific/Galapagos":{"offset":-360,"msg":{"standard":"Galapagos Time"}},"America/Bogota":{"offset":-300},"America/Cancun":{"offset":-300},"America/Cayman":{"offset":-300},"America/Guayaquil":{"offset":-300},"America/Havana":{"offset":-300},"America/Iqaluit":{"offset":-300},"America/Jamaica":{"offset":-300},"America/Lima":{"offset":-300},"America/Nassau":{"offset":-300},"America/New_York":{"offset":-300},"America/Panama":{"offset":-300},"America/Port-au-Prince":{"offset":-300},"America/Rio_Branco":{"offset":-300},"America/Toronto":{"offset":-300},"Pacific/Easter":{"offset":-300,"msg":{"generic":"Easter Island Time","standard":"Easter Island Standard Time","daylight":"Easter Island Summer Time"}},"America/Caracas":{"offset":-210},"America/Asuncion":{"offset":-180},"America/Barbados":{"offset":-240},"America/Boa_Vista":{"offset":-240},"America/Campo_Grande":{"offset":-180},"America/Cuiaba":{"offset":-180},"America/Curacao":{"offset":-240},"America/Grand_Turk":{"offset":-240},"America/Guyana":{"offset":-240,"msg":{"standard":"Guyana Time"}},"America/Halifax":{"offset":-240},"America/La_Paz":{"offset":-240},"America/Manaus":{"offset":-240},"America/Martinique":{"offset":-240},"America/Port_of_Spain":{"offset":-240},"America/Porto_Velho":{"offset":-240},"America/Puerto_Rico":{"offset":-240},"America/Santo_Domingo":{"offset":-240},"America/Thule":{"offset":-240},"Atlantic/Bermuda":{"offset":-240},"America/St_Johns":{"offset":-150},"America/Araguaina":{"offset":-180},"America/Argentina/Buenos_Aires":{"offset":-180,"msg":{"generic":"Argentina Time","standard":"Argentina Standard Time","daylight":"Argentina Summer Time"}},"America/Bahia":{"offset":-180},"America/Belem":{"offset":-180},"America/Cayenne":{"offset":-180},"America/Fortaleza":{"offset":-180},"America/Godthab":{"offset":-180},"America/Maceio":{"offset":-180},"America/Miquelon":{"offset":-180},"America/Montevideo":{"offset":-180},"America/Paramaribo":{"offset":-180},"America/Recife":{"offset":-180},"America/Santiago":{"offset":-180},"America/Sao_Paulo":{"offset":-120},"Antarctica/Palmer":{"offset":-180},"Antarctica/Rothera":{"offset":-180,"msg":{"standard":"Rothera Time"}},"Atlantic/Stanley":{"offset":-180},"America/Noronha":{"offset":-120,"msg":{"generic":"Fernando de Noronha Time","standard":"Fernando de Noronha Standard Time","daylight":"Fernando de Noronha Summer Time"}},"Atlantic/South_Georgia":{"offset":-120,"msg":{"standard":"South Georgia Time"}},"America/Scoresbysund":{"offset":-60},"Atlantic/Azores":{"offset":-60,"msg":{"generic":"Azores Time","standard":"Azores Standard Time","daylight":"Azores Summer Time"}},"Atlantic/Cape_Verde":{"offset":-60,"msg":{"generic":"Cape Verde Time","standard":"Cape Verde Standard Time","daylight":"Cape Verde Summer Time"}},"Africa/Abidjan":{"offset":0},"Africa/Accra":{"offset":0},"Africa/Bissau":{"offset":0},"Africa/Casablanca":{"offset":0},"Africa/El_Aaiun":{"offset":0},"Africa/Monrovia":{"offset":0},"America/Danmarkshavn":{"offset":0},"Atlantic/Canary":{"offset":0},"Atlantic/Faroe":{"offset":0},"Atlantic/Reykjavik":{"offset":0},"Etc/GMT":{"offset":0,"msg":{"standard":"Greenwich Mean Time"}},"Europe/Dublin":{"offset":0},"Europe/Lisbon":{"offset":0},"Europe/London":{"offset":0},"Africa/Algiers":{"offset":60},"Africa/Ceuta":{"offset":60},"Africa/Lagos":{"offset":60},"Africa/Ndjamena":{"offset":60},"Africa/Tunis":{"offset":60},"Africa/Windhoek":{"offset":120},"Europe/Amsterdam":{"offset":60},"Europe/Andorra":{"offset":60},"Europe/Belgrade":{"offset":60},"Europe/Berlin":{"offset":60},"Europe/Brussels":{"offset":60},"Europe/Budapest":{"offset":60},"Europe/Copenhagen":{"offset":60},"Europe/Gibraltar":{"offset":60},"Europe/Luxembourg":{"offset":60},"Europe/Madrid":{"offset":60},"Europe/Malta":{"offset":60},"Europe/Monaco":{"offset":60},"Europe/Oslo":{"offset":60},"Europe/Paris":{"offset":60},"Europe/Prague":{"offset":60},"Europe/Rome":{"offset":60},"Europe/Stockholm":{"offset":60},"Europe/Tirane":{"offset":60},"Europe/Vienna":{"offset":60},"Europe/Warsaw":{"offset":60},"Europe/Zurich":{"offset":60},"Africa/Cairo":{"offset":120},"Africa/Johannesburg":{"offset":120},"Africa/Maputo":{"offset":120},"Africa/Tripoli":{"offset":120},"Asia/Amman":{"offset":120},"Asia/Beirut":{"offset":120},"Asia/Damascus":{"offset":120},"Asia/Gaza":{"offset":120},"Asia/Jerusalem":{"offset":120},"Asia/Nicosia":{"offset":120},"Europe/Athens":{"offset":120},"Europe/Bucharest":{"offset":120},"Europe/Chisinau":{"offset":120},"Europe/Helsinki":{"offset":120},"Europe/Istanbul":{"offset":120},"Europe/Kaliningrad":{"offset":120},"Europe/Kiev":{"offset":120},"Europe/Riga":{"offset":120},"Europe/Sofia":{"offset":120},"Europe/Tallinn":{"offset":120},"Europe/Vilnius":{"offset":120},"Africa/Khartoum":{"offset":180},"Africa/Nairobi":{"offset":180},"Antarctica/Syowa":{"offset":180,"msg":{"standard":"Syowa Time"}},"Asia/Baghdad":{"offset":180},"Asia/Qatar":{"offset":180},"Asia/Riyadh":{"offset":180},"Europe/Minsk":{"offset":180},"Europe/Moscow":{"offset":180,"msg":{"generic":"Moscow Time","standard":"Moscow Standard Time","daylight":"Moscow Summer Time"}},"Asia/Tehran":{"offset":210},"Asia/Baku":{"offset":240},"Asia/Dubai":{"offset":240},"Asia/Tbilisi":{"offset":240},"Asia/Yerevan":{"offset":240},"Europe/Samara":{"offset":240,"msg":{"generic":"Samara Time","standard":"Samara Standard Time","daylight":"Samara Summer Time"}},"Indian/Mahe":{"offset":240},"Indian/Mauritius":{"offset":240,"msg":{"generic":"Mauritius Time","standard":"Mauritius Standard Time","daylight":"Mauritius Summer Time"}},"Indian/Reunion":{"offset":240,"msg":{"standard":"Réunion Time"}},"Asia/Kabul":{"offset":270},"Antarctica/Mawson":{"offset":300,"msg":{"standard":"Mawson Time"}},"Asia/Aqtau":{"offset":300,"msg":{"generic":"Aqtau Time","standard":"Aqtau Standard Time","daylight":"Aqtau Summer Time"}},"Asia/Aqtobe":{"offset":300,"msg":{"generic":"Aqtobe Time","standard":"Aqtobe Standard Time","daylight":"Aqtobe Summer Time"}},"Asia/Ashgabat":{"offset":300},"Asia/Dushanbe":{"offset":300},"Asia/Karachi":{"offset":300},"Asia/Tashkent":{"offset":300},"Asia/Yekaterinburg":{"offset":300,"msg":{"generic":"Yekaterinburg Time","standard":"Yekaterinburg Standard Time","daylight":"Yekaterinburg Summer Time"}},"Indian/Kerguelen":{"offset":300},"Indian/Maldives":{"offset":300,"msg":{"standard":"Maldives Time"}},"Asia/Calcutta":{"offset":330},"Asia/Colombo":{"offset":330},"Asia/Katmandu":{"offset":345},"Antarctica/Vostok":{"offset":360,"msg":{"standard":"Vostok Time"}},"Asia/Almaty":{"offset":360,"msg":{"generic":"Almaty Time","standard":"Almaty Standard Time","daylight":"Almaty Summer Time"}},"Asia/Bishkek":{"offset":360},"Asia/Dhaka":{"offset":360},"Asia/Omsk":{"offset":360,"msg":{"generic":"Omsk Time","standard":"Omsk Standard Time","daylight":"Omsk Summer Time"}},"Asia/Thimphu":{"offset":360},"Indian/Chagos":{"offset":360},"Asia/Rangoon":{"offset":390},"Indian/Cocos":{"offset":390,"msg":{"standard":"Cocos Islands Time"}},"Antarctica/Davis":{"offset":420,"msg":{"standard":"Davis Time"}},"Asia/Bangkok":{"offset":420},"Asia/Hovd":{"offset":420,"msg":{"generic":"Hovd Time","standard":"Hovd Standard Time","daylight":"Hovd Summer Time"}},"Asia/Jakarta":{"offset":420},"Asia/Krasnoyarsk":{"offset":420,"msg":{"generic":"Krasnoyarsk Time","standard":"Krasnoyarsk Standard Time","daylight":"Krasnoyarsk Summer Time"}},"Asia/Saigon":{"offset":420},"Indian/Christmas":{"offset":420,"msg":{"standard":"Christmas Island Time"}},"Antarctica/Casey":{"offset":480,"msg":{"standard":"Casey Time"}},"Asia/Brunei":{"offset":480,"msg":{"standard":"Brunei Darussalam Time"}},"Asia/Choibalsan":{"offset":480,"msg":{"generic":"Choibalsan Time","standard":"Choibalsan Standard Time","daylight":"Choibalsan Summer Time"}},"Asia/Hong_Kong":{"offset":480,"msg":{"generic":"Hong Kong Time","standard":"Hong Kong Standard Time","daylight":"Hong Kong Summer Time"}},"Asia/Irkutsk":{"offset":480,"msg":{"generic":"Irkutsk Time","standard":"Irkutsk Standard Time","daylight":"Irkutsk Summer Time"}},"Asia/Kuala_Lumpur":{"offset":480},"Asia/Macau":{"offset":480,"msg":{"generic":"Macau Time","standard":"Macau Standard Time","daylight":"Macau Summer Time"}},"Asia/Makassar":{"offset":480},"Asia/Manila":{"offset":480},"Asia/Shanghai":{"offset":480},"Asia/Singapore":{"offset":480,"msg":{"standard":"Singapore Standard Time"}},"Asia/Taipei":{"offset":480,"msg":{"generic":"Taipei Time","standard":"Taipei Standard Time","daylight":"Taipei Daylight Time"}},"Asia/Ulaanbaatar":{"offset":480},"Australia/Perth":{"offset":480},"Asia/Pyongyang":{"offset":510,"msg":{"standard":"Pyongyang Time"}},"Asia/Dili":{"offset":540},"Asia/Jayapura":{"offset":540},"Asia/Seoul":{"offset":540},"Asia/Tokyo":{"offset":540},"Asia/Yakutsk":{"offset":540,"msg":{"generic":"Yakutsk Time","standard":"Yakutsk Standard Time","daylight":"Yakutsk Summer Time"}},"Pacific/Palau":{"offset":540,"msg":{"standard":"Palau Time"}},"Australia/Adelaide":{"offset":630},"Australia/Darwin":{"offset":570},"Antarctica/DumontDUrville":{"offset":600,"msg":{"standard":"Dumont-d’Urville Time"}},"Asia/Magadan":{"offset":600,"msg":{"generic":"Magadan Time","standard":"Magadan Standard Time","daylight":"Magadan Summer Time"}},"Asia/Vladivostok":{"offset":600,"msg":{"generic":"Vladivostok Time","standard":"Vladivostok Standard Time","daylight":"Vladivostok Summer Time"}},"Australia/Brisbane":{"offset":600},"Australia/Hobart":{"offset":660},"Australia/Sydney":{"offset":660},"Pacific/Chuuk":{"offset":600},"Pacific/Guam":{"offset":600,"msg":{"standard":"Guam Standard Time"}},"Pacific/Port_Moresby":{"offset":600},"Pacific/Efate":{"offset":660},"Pacific/Guadalcanal":{"offset":660},"Pacific/Kosrae":{"offset":660,"msg":{"standard":"Kosrae Time"}},"Pacific/Norfolk":{"offset":660,"msg":{"standard":"Norfolk Island Time"}},"Pacific/Noumea":{"offset":660},"Pacific/Pohnpei":{"offset":660},"Asia/Kamchatka":{"offset":720,"msg":{"generic":"Petropavlovsk-Kamchatski Time","standard":"Petropavlovsk-Kamchatski Standard Time","daylight":"Petropavlovsk-Kamchatski Summer Time"}},"Pacific/Auckland":{"offset":780},"Pacific/Fiji":{"offset":780,"msg":{"generic":"Fiji Time","standard":"Fiji Standard Time","daylight":"Fiji Summer Time"}},"Pacific/Funafuti":{"offset":720},"Pacific/Kwajalein":{"offset":720},"Pacific/Majuro":{"offset":720},"Pacific/Nauru":{"offset":720,"msg":{"standard":"Nauru Time"}},"Pacific/Tarawa":{"offset":720},"Pacific/Wake":{"offset":720,"msg":{"standard":"Wake Island Time"}},"Pacific/Wallis":{"offset":720,"msg":{"standard":"Wallis & Futuna Time"}},"Pacific/Apia":{"offset":840,"msg":{"generic":"Apia Time","standard":"Apia Standard Time","daylight":"Apia Daylight Time"}},"Pacific/Enderbury":{"offset":780},"Pacific/Fakaofo":{"offset":780},"Pacific/Tongatapu":{"offset":780},"Pacific/Kiritimati":{"offset":840}}
    timezone = 'Australia/Brisbane'
    if timezone not in timezoneDict:
      timezone = 'America/New_York'
    timezoneCountry = timezoneDict[timezone]
    timezoneOffset = timezoneCountry['offset']
    country = timezone.split('/')[1].replace('_', ' ').replace('-', ' ')
    timeZoneArray = "['%s', -1 * %s, new Date().getTimezoneOffset(), '%s']" % (timezone, timezoneOffset, country+' Standard Time')
    canvas_js = canvas_js.replace('{{timeZoneArray}}', str(timeZoneArray))
    #
    list_floats = [math.pow(2, 0), math.pow(2, 10), math.pow(2, 11), math.pow(2, 12), math.pow(2, 13)];
    list_int = [math.pow(2, 13), math.pow(2, 14), math.pow(2, 15)]
    int_3386 = int(list_int[random.randint(0, len(list_int) - 1)])
    list_1234 = [math.pow(2, 1), math.pow(2, 2), math.pow(2, 3), math.pow(2, 4)]
    list_1415 = [math.pow(2, 14), math.pow(2, 15)]
    list_1213 = [math.pow(2, 12), math.pow(2, 13)]
    list_45678 = [math.pow(2, 4), math.pow(2, 5), math.pow(2, 6), math.pow(2, 7), math.pow(2, 8)]
    list_10111213 = [math.pow(2, 10), math.pow(2, 11), math.pow(2, 12), math.pow(2, 13)]
    webgl_replace = {}
    webgl_replace['36347'] = int(list_1213[random.randint(0, len(list_1213) - 1)])
    webgl_replace['3379'] = int(list_1415[random.randint(0, len(list_1415) - 1)])
    webgl_replace['34076'] = int(list_1415[random.randint(0, len(list_1415) - 1)])
    webgl_replace['34024'] = int(list_1415[random.randint(0, len(list_1415) - 1)])
    webgl_replace['35661'] = int(list_45678[random.randint(0, len(list_45678) - 1)])
    webgl_replace['36349'] = int(list_10111213[random.randint(0, len(list_10111213) - 1)])
    webgl_replace['3413'] = int(list_1234[random.randint(0, len(list_1234) - 1)])
    webgl_replace['3412'] = int(list_1234[random.randint(0, len(list_1234) - 1)])
    webgl_replace['3411'] = int(list_1234[random.randint(0, len(list_1234) - 1)])
    webgl_replace['3410'] = int(list_1234[random.randint(0, len(list_1234) - 1)])
    webgl_replace['35660'] = int(list_1234[random.randint(0, len(list_1234) - 1)])
    webgl_replace['34047'] = int(list_1234[random.randint(0, len(list_1234) - 1)])
    webgl_replace['34930'] = int(list_1234[random.randint(0, len(list_1234) - 1)])
    webgl_replace['34921'] = int(list_1234[random.randint(0, len(list_1234) - 1)])
    webgl_replace['3386'] = [int_3386, int_3386]
    webgl_replace['33901'] = [random.uniform(0.01, 1), list_floats[random.randint(0, len(list_floats) - 1)]]
    webgl_replace['33902'] = [random.uniform(0.01, 1), list_floats[random.randint(0, len(list_floats) - 1)]]
    webgl_replace['34324'] = random.uniform(0.01, 0.99)
    webgl_replace['35376'] = random.uniform(0.01, 0.99)
    webgl_replace['35377'] = random.uniform(0.01, 0.99)
    webgl_replace['35379'] = random.uniform(0.01, 0.99)
    webgl_replace['35658'] = random.uniform(0.01, 0.99)
    webgl_replace['gl_index'] = random.uniform(0.01, 0.99)
    webgl_replace['gl_noise'] = random.uniform(0.01, 0.99)
    list_vgas = ['ANGLE (NVIDIA Quadro 2000M Direct3D11 vs_5_0 ps_5_0)','ANGLE (NVIDIA Quadro K420 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA Quadro 2000M Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA Quadro K2000M Direct3D11 vs_5_0 ps_5_0)','ANGLE (Intel(R) HD Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 3800 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 4000 Direct3D11 vs_5_0 ps_5_0)','ANGLE (Intel(R) HD Graphics 4000 Direct3D11 vs_5_0 ps_5_0)','ANGLE (AMD Radeon R9 200 Series Direct3D11 vs_5_0 ps_5_0)','ANGLE (Intel(R) HD Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 4000 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 3000 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Mobile Intel(R) 4 Series Express Chipset Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G33/G31 Express Chipset Family Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (Intel(R) Graphics Media Accelerator 3150 Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (Intel(R) G41 Express Chipset Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 6150SE nForce 430 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 4000)','ANGLE (Mobile Intel(R) 965 Express Chipset Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family)','ANGLE (NVIDIA GeForce GTX 760 Direct3D11 vs_5_0 ps_5_0)','ANGLE (NVIDIA GeForce GTX 760 Direct3D11 vs_5_0 ps_5_0)','ANGLE (NVIDIA GeForce GTX 760 Direct3D11 vs_5_0 ps_5_0)','ANGLE (AMD Radeon HD 6310 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Graphics Media Accelerator 3600 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G33/G31 Express Chipset Family Direct3D9 vs_0_0 ps_2_0)','ANGLE (AMD Radeon HD 6320 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G33/G31 Express Chipset Family (Microsoft Corporation - WDDM 1.0) Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (Intel(R) G41 Express Chipset)','ANGLE (ATI Mobility Radeon HD 5470 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q45/Q43 Express Chipset Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 310M Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G41 Express Chipset Direct3D9 vs_3_0 ps_3_0)','ANGLE (Mobile Intel(R) 45 Express Chipset Family (Microsoft Corporation - WDDM 1.1) Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 440 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 4300/4500 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7310 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics)','ANGLE (Intel(R) 4 Series Internal Chipset Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon(TM) HD 6480G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 3200 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7800 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G41 Express Chipset (Microsoft Corporation - WDDM 1.1) Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 210 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 630 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7340 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) 82945G Express Chipset Family Direct3D9 vs_0_0 ps_2_0)','ANGLE (NVIDIA GeForce GT 430 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 7025 / NVIDIA nForce 630a Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q35 Express Chipset Family Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (Intel(R) HD Graphics 4600 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7520G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD 760G (Microsoft Corporation WDDM 1.1) Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 220 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 9500 GT Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family Direct3D9 vs_3_0 ps_3_0)','ANGLE (Intel(R) Graphics Media Accelerator HD Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 9800 GT Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q965/Q963 Express Chipset Family (Microsoft Corporation - WDDM 1.0) Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (NVIDIA GeForce GTX 550 Ti Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q965/Q963 Express Chipset Family Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (AMD M880G with ATI Mobility Radeon HD 4250 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GTX 650 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Mobility Radeon HD 5650 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 4200 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7700 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G33/G31 Express Chipset Family)','ANGLE (Intel(R) 82945G Express Chipset Family Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (SiS Mirage 3 Graphics Direct3D9Ex vs_2_0 ps_2_0)','ANGLE (NVIDIA GeForce GT 430)','ANGLE (AMD RADEON HD 6450 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon 3000 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) 4 Series Internal Chipset Direct3D9 vs_3_0 ps_3_0)','ANGLE (Intel(R) Q35 Express Chipset Family (Microsoft Corporation - WDDM 1.0) Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (NVIDIA GeForce GT 220 Direct3D9 vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7640G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD 760G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 6450 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 640 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 9200 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 610 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 6290 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Mobility Radeon HD 4250 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 8600 GT Direct3D9 vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 5570 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 6800 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G45/G43 Express Chipset Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 4600 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA Quadro NVS 160M Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 3000)','ANGLE (NVIDIA GeForce G100)','ANGLE (AMD Radeon HD 8610G + 8500M Dual Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Mobile Intel(R) 4 Series Express Chipset Family Direct3D9 vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 7025 / NVIDIA nForce 630a (Microsoft Corporation - WDDM) Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q965/Q963 Express Chipset Family Direct3D9 vs_0_0 ps_2_0)','ANGLE (AMD RADEON HD 6350 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 5450 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 9500 GT)','ANGLE (AMD Radeon HD 6500M/5600/5700 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Mobile Intel(R) 965 Express Chipset Family)','ANGLE (NVIDIA GeForce 8400 GS Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Direct3D9 vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GTX 560 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 620 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GTX 660 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon(TM) HD 6520G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 240 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 8240 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA Quadro NVS 140M)','ANGLE (Intel(R) Q35 Express Chipset Family Direct3D9 vs_0_0 ps_2_0)']
    webgl_replace['37446'] = list_vgas[random.randint(0, len(list_vgas) - 1)]
    list_es = ["WebGL 2.0 (OpenGL ES 3.0 Chromium)"]
    list_glsl = ["WebGL GLSL ES (OpenGL Chromium)","WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)"]
    webgl_replace['7938'] = list_es[random.randint(0, len(list_es) - 1)]
    webgl_replace['35724'] = list_glsl[random.randint(0, len(list_glsl) - 1)]
    gpu_vendor = "Google Inc. (ATI Technologies Inc.)"
    webgl_replace['37445'] = gpu_vendor
    
    for key in webgl_replace.keys():
      canvas_js = canvas_js.replace('{{'+key+'}}', str(webgl_replace[key]))
      
    set_device_metrics_override = dict({
                    "width": screen_width,
                    "height": screen_height,
                    "screenWidth":screen_width,
                    "screenHeight":screen_height,
                    "deviceScaleFactor": 0,
                    "mobile": False
                })
    driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', set_device_metrics_override)
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': canvas_js,'includeCommandLineAPI':True})
    
    #set platform
    set_navigator_override = dict({
      'platform':"MacIntel"
    })
    driver.execute_cdp_cmd('Emulation.setNavigatorOverrides', set_navigator_override)
    
    #set setHardwareConcurrencyOverride
    
    set_hardware_override = dict({
      'hardwareConcurrency':6
    })
    driver.execute_cdp_cmd('Emulation.setHardwareConcurrencyOverride', set_hardware_override)
    #config.random.float([0, 10, 11, 12, 13])

    url = "https://bot.sannysoft.com/"
    driver.get(url)

    last_leng_window = driver.window_handles
    while 1:
        leng_window = driver.window_handles
        # print(leng_window)
        if last_leng_window != leng_window and len(leng_window) != 0:
            driver.switch_to.window(driver.window_handles[-1])
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument',
                                   {'source': canvas_js, 'includeCommandLineAPI': True})
            driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', set_device_metrics_override)

            last_leng_window = driver.window_handles
        if len(leng_window) == 0:
          break
        
        
    driver.quit()

BrowserSelenium()