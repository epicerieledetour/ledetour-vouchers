STATE = null

window.addEventListener('load', () => start(), false)
window.addEventListener('load', () => setup_scanner(), false)

async function setup_scanner() {
    const scanPreviewElem = document.getElementById('scan-preview')

    // Debug feature: if an URL fragment is present (#some-voucher-id), then clicking
    // on the video preview will trigger a process of the code defined by the fragment

    scanPreviewElem.addEventListener("click", () => {
        const url_code = window.location.hash.substring(1)
        if (url_code) {
            process_code(url_code)
        }
    })

    // Setup the action button

    const actionButtonElem = document.getElementById('action')
    actionButtonElem.addEventListener("click", process_button)

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

async function process_code(code) {
    await process_action(STATE.next_actions.scan, code)
}

async function process_button() {
    await process_action(STATE.next_actions.button)
}

async function process_action(action, code) {
    if (!action) {
        return
    }

    const options = {
        method: action.verb
    }
    if (action.body) {
        options.body = JSON.stringify(action.body)
    }
    const url = code ? action.url.replace("{code}", code) : action.url

    await query(url, options)
}

async function start() {
    await query("/start")
}

async function query(url, options) {
    options = options || {}
    options.headers = options.headers || {}
    options.headers["Accept"] = 'application/json, */*;q=0.5'
    options.headers['Content-Type'] = 'application/json;charset=utf-8'

    if (STATE && STATE.user) {
        options.headers["Authorization"] = "Bearer " + STATE.user.id
    }
    const response = await fetch(url, options)
    if (response.ok) {
        STATE = await response.json()
        refresh()
    } else {
        console.error(response)
    }
}

function refresh() {
    const header = document.getElementById('header')
    set_visible(header, Boolean(STATE.user))

    const voucher = document.getElementById('voucher')
    set_visible(voucher, Boolean(STATE.voucher))

    const message = document.getElementById('message')
    set_message(message, STATE.message_main)
    set_visible(message, Boolean(STATE.message_main))

    const detail = document.getElementById('detail')
    set_message(detail, STATE.message_detail)
    set_visible(detail, Boolean(STATE.message_detail))

    const action = document.getElementById('action')
    action_button = STATE.next_actions.button
    set_message(action, action_button ? action_button.message : null)
    set_visible(action, Boolean(action_button))
}

function set_severity_class(el, severity) {
    el.classList.remove("severity-0")
    el.classList.remove("severity-1")
    el.classList.remove("severity-2")
    el.classList.remove("severity-3")
    el.classList.add("severity-" + severity)
}

function set_visible(el, visibility) {
    if (visibility) {
        el.classList.remove("invisible")
    }
    else {
        el.classList.add("invisible")
    }
}

function set_message(el, message) {
    if (message) {
        el.textContent = message.text
        set_severity_class(el, message.severity)
    } else {
        el.textContent = ""
    }
}