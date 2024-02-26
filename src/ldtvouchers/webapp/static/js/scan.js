window.addEventListener('load', () => setupScanner(), false)

function scanUrl() {
    const meta = document.querySelector("meta[name=scan-url]")
    return meta ? meta.content : null
}

async function setupScanner() {
    const scanPreviewElem = document.getElementById('scan-preview')

    // Debug feature: if an URL fragment is present (#some-voucher-id), then clicking
    // on the video preview will trigger a process of the code defined by the fragment

    scanPreviewElem.addEventListener("click", () => {
        const scanResult = window.location.hash.substring(1)
        if (scanResult) {
            processScanResult(scanResult)
        }
    })

    // Barcode scanning setup

    const reader = new ZXingBrowser.BrowserQRCodeReader()
    reader.timeBetweenScansMillis = 1000

    // passing a null deviceID forces the "environment" facingMode
    // https://developer.mozilla.org/en-US/docs/Web/API/MediaTrackConstraints/facingMode
    // https://github.com/zxing-js/library/blob/master/src/browser/BrowserCodeReader.ts#L316
    await reader.decodeFromVideoDevice(null, scanPreviewElem, scanDecodeCallback)
}

async function scanDecodeCallback(result) {
    if (result) {
        processScanResult(result.text)
    }
}

function processScanResult(scanResult) {
    let url = scanUrl()
    if (!url) {
        console.warn(`Request to process scan result "${scanResult}" but no scan url has been found.`)
        return
    }
    url = url.replace("{scanResult}", scanResult)
    window.location.href = url
}

function show_history() {
    const dialogTitleElem = document.getElementById('dialog-title')
    dialogTitleElem.textContent = "History"

    const dialogContentElem = document.getElementById('dialog-content')
    dialogContentElem.innerHTML = '';

    if (STATE.voucher) {
        STATE.voucher.history.forEach(el => {
            const p = document.createElement("p")
            p.textContent = el
            dialogContentElem.appendChild(p)
        })
    }

    const dialogElem = document.getElementById('dialog')
    dialogElem.open = true
}
