/* Cloud controls live outside the app iframe. Only alter this app's same-origin
   Cloud shell, never an unrelated embedding page or the app sidebar. */
(() => {
  if (!location.hostname.endsWith('.streamlit.app')) return;
  const normalize = value => (value || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const isManage = value => normalize(value) === 'manage app';
  const documents = [document];
  try {
    if (window.parent !== window && window.parent.location.origin === location.origin) {
      documents.push(window.parent.document);
    }
  } catch (_) { /* An unrelated cross-origin embed must remain untouched. */ }
  for (const doc of documents) {
    if (doc.getElementById('flood-map-cloud-controls')) continue;
    const style = doc.createElement('style');
    style.id = 'flood-map-cloud-controls';
    style.textContent = '[data-flood-map-owner-control="hidden"] { display:none !important; }';
    doc.head.appendChild(style);
    const hideManage = () => {
      for (const element of doc.querySelectorAll('button,a,[role="button"],summary')) {
        if (isManage(element.textContent) || isManage(element.getAttribute('aria-label')) ||
            isManage(element.getAttribute('title'))) {
          element.setAttribute('data-flood-map-owner-control', 'hidden');
        }
      }
      // Some Cloud versions render the owner action as an unlabelled div/span.
      for (const element of doc.querySelectorAll('span,div')) {
        if (element.children.length || !isManage(element.textContent)) continue;
        const control = element.closest('button,a,[role="button"]') || element;
        control.setAttribute('data-flood-map-owner-control', 'hidden');
      }
    };
    hideManage();
    // Owner controls may arrive after app startup or reappear on a Cloud rerender.
    // Do not observe attributes: marking an element must not retrigger the observer.
    let scheduled = false;
    const observer = new MutationObserver(() => {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(() => { scheduled = false; hideManage(); });
    });
    observer.observe(doc.body, {subtree:true, childList:true, characterData:true});
  }
})();
