// MunAntiBrowser - Audio Fingerprint Noise
// Modifies AudioContext output to create unique audio fingerprint.
// Templates: {{audio_content}}, {{audio_random1}}, {{audio_random2}}

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
              results_1[key] = obj2[key];
            }
          }
          return results_1;
        }, configurable: true, writable: true
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
                arguments[0][index] = new_value;
              }
              return results_3;
            }, configurable: true, writable: true
          });
          return results_2;
        }, configurable: true, writable: true
      });
    }
  };

  context.getChannelData(AudioBuffer);
  context.createAnalyser(AudioContext);
  context.getChannelData(OfflineAudioContext);
  context.createAnalyser(OfflineAudioContext);
})();
