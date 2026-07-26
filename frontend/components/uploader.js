// Handles uploading a claim document (photo/report/invoice) to
// /claims/{id}/documents and showing the OCR/damage check result.

async function uploadDocument(claimId, docType, fileInputId, resultBoxId) {
  const fileInput = document.getElementById(fileInputId);
  const resultBox = document.getElementById(resultBoxId);
  const file = fileInput.files[0];
  if (!file) return;

  const form = new FormData();
  form.append("doc_type", docType);
  form.append("file", file);

  resultBox.textContent = "Uploading and checking...";
  try {
    const result = await Api.request(`/claims/${claimId}/documents`, { method: "POST", body: form, form: true });
    resultBox.textContent = JSON.stringify(result.result);
  } catch (err) {
    resultBox.textContent = `Error: ${err.message}`;
  }
}
