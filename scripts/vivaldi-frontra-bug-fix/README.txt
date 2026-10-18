In the Vivaldi browser, keyboard shortcuts do not work in the Frontra web app. The reason is that Vivaldi passes an empty map to `navigator.keyboard.getLayoutMap()`. This mini-plugin fixes the issue for Frontra at http://localhost:8000.

To install, open vivaldi://extensions, enable developer mode, and select “Load unpacked extension.” The extension containing the fix must remain in its location afterward. 

Translated with DeepL.com (free version)