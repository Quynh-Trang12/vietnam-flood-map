/* Hide guest branding in the same-origin Community Cloud shell.
   Owner management controls and unrelated embedding pages remain untouched. */
(() => {
  if (!location.hostname.endsWith('.streamlit.app')) return;
  const documents = [document];
  try {
    if (window.parent !== window && window.parent.location.origin === location.origin) {
      documents.push(window.parent.document);
    }
  } catch (_) { /* Do not modify a cross-origin embedding page. */ }
  const guestBadgeCSS = `
    [class*="_viewerBadge_"],
    [class*="_profileContainer_"]:has([data-testid="appCreatorAvatar"]) {
      display:none !important;
    }
  `;
  for (const doc of documents) {
    let style = doc.getElementById('flood-map-guest-branding');
    if (!style) {
      style = doc.createElement('style');
      style.id = 'flood-map-guest-branding';
      doc.head.appendChild(style);
    }
    style.textContent = guestBadgeCSS;
  }
})();
