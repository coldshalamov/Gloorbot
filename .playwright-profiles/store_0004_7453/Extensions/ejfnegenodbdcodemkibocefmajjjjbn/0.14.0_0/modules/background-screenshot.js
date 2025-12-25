// Import helper functions from background-commands
import { getElement, getTabInfo, respondWithError, attachDebugger } from './background-commands.js';

export async function screenshot({tabId}, { scale = 0.5, quality = 0.5, format = 'webp', selector, xpath }) {
  let elementResult;
  if (selector || xpath) {
    elementResult = await getElement(tabId, selector, xpath, true);
    if (elementResult.error) return elementResult;
  }
  else {
    elementResult = await getTabInfo(tabId)
    elementResult.element = {
      bounds: {
        x: elementResult.scrollPosition.x,
        y: elementResult.scrollPosition.y,
        width: elementResult.viewportDimensions.width,
        height: elementResult.viewportDimensions.height
      }
    };
  }

  const clip = elementResult.element.bounds;
  if (scale) {
    clip.scale = scale;
  }

  return attachDebugger(tabId, async () => {
    const screenshot = await chrome.debugger.sendCommand({ tabId }, 'Page.captureScreenshot', {
      format,
      quality: Math.round(quality * 100), // Chrome needs an integer percentage,
      clip
    });

    return {
      ...elementResult,
      element: undefined,
      selector: elementResult.element?.selector || undefined,
      mimeType: `image/${format}`,
      data: screenshot.data,
    };
  })
  .catch((err) => {
    return respondWithError(tabId,'SCREENSHOT_ERROR', err.message, null, null);
  });
}