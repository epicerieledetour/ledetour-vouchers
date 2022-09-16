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

    // Setup the exit button

    const exitButtonElem = document.getElementById('exit')
    exitButtonElem.addEventListener("click", start)

    // Setup the action button

    const actionButtonElem = document.getElementById('action')
    actionButtonElem.addEventListener("click", process_button)

    // Setup the history button

    const historyButtonElem = document.getElementById('history')
    historyButtonElem.addEventListener("click", show_history)

    // Setup the dialog

    const dialogElem = document.getElementById('dialog')
    dialogElem.addEventListener("click", (el) => {
        el.currentTarget.open = false
    }, false)

    // Barcode scanning setup

    const codeReader = new ZXing.BrowserMultiFormatReader()
    codeReader.timeBetweenScansMillis = 3000

    async function setVideoDevice(deviceId) {
        const controls = await codeReader.decodeFromVideoDevice(deviceId, scanPreviewElem, async (result, err) => {
            // TODO: handle error
            if (result) {
                await process_code(result.text)
            }
        })
        return controls
    }

    const videoInputDevices = await codeReader.listVideoInputDevices();
    if (videoInputDevices.length == 0) {
        // TODO: show error message
        return
    }

    if (videoInputDevices.length > 0) {
        await setVideoDevice(videoInputDevices[videoInputDevices.length - 1].deviceId)
    }

    if (videoInputDevices.length > 1) {
        const cameraSelectorElem = document.getElementById('camera-selector')
        for (let i = 0; i < videoInputDevices.length; i++) {
            const videoDevice = videoInputDevices[i]
            const buttonElem = document.createElement("BUTTON");
            buttonElem.textContent = videoDevice.label
            buttonElem.addEventListener("click", async (el) => {
                await setVideoDevice(videoDevice.deviceId)
            }, false)
            cameraSelectorElem.appendChild(buttonElem)
        }
    }
}

async function process_code(code) {
    // After a first successful scan the selected camera is expected to stay
    // valid until the rest of the session, so the camera-selector can be hidden
    document.getElementById("camera-selector").style.visibility = "hidden"
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
    await query("/api/start")
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

    const user = document.getElementById('user')
    if (STATE.user) {
        user.textContent = STATE.user.description
    }

    const history = document.getElementById('history')
    set_visible(history, Boolean(STATE.voucher))

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
