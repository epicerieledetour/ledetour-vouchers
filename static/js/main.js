window.addEventListener('load', () => main(), false)


async function main() {
    const scanPreviewElem = document.getElementById('scan-preview');

    // Debug feature: if an URL fragment is present (#some-voucher-id), then clicking
    // on the video preview will trigger a process of the code defined by the fragment

    const url_code = window.location.hash.substring(1);
    if (url_code) {
        scanPreviewElem.addEventListener("click", () => process_code(url_code));
    }

    // Barcode scanning setup

    const codeReader = new ZXing.BrowserMultiFormatReader()
    const videoInputDevices = await codeReader.listVideoInputDevices();

    // TODO: let the user choose what camera to use
    const selectedDeviceId = videoInputDevices[1].deviceId;

    const controls = await codeReader.decodeFromVideoDevice(selectedDeviceId, scanPreviewElem, async (result, err) => {
        // TODO: handle error
        if (result) {
            await process_code(result.txt)
        }
    })
}

async function process_code(text) {
    console.log(text)
}
