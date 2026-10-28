/**
 * SentinelIQ Vanilla JavaScript Utilities
 * Minimal, dependency-free interactive enhancements for forms and notifications.
 */

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    alert("Copied to clipboard: " + text);
  }).catch(err => {
    console.error("Failed to copy: ", err);
  });
}

async function apiPost(endpoint, body) {
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Request failed with status " + res.status);
    }
    return data;
  } catch (err) {
    alert("Error: " + err.message);
    throw err;
  }
}

async function apiPatch(endpoint, body) {
  try {
    const res = await fetch(endpoint, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Request failed with status " + res.status);
    }
    return data;
  } catch (err) {
    alert("Error: " + err.message);
    throw err;
  }
}
