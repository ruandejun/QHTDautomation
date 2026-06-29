// MunAntiBrowser - Speech Synthesis Voices Spoof
// Limits speech synthesis voices to prevent unique fingerprint.

(function fakeSpeechSynthesis() {
  try {
    if (typeof window.speechSynthesis !== 'undefined') {
      var originalGetVoices = window.speechSynthesis.getVoices.bind(window.speechSynthesis);
      Object.defineProperty(window.speechSynthesis, 'getVoices', {
        value: function() {
          var voices = originalGetVoices();
          return voices.slice(0, Math.min(voices.length, 3));
        },
        configurable: true, writable: true
      });
    }
  } catch(e) {}
})();
