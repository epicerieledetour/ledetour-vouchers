STATE = null
CODE_READER = null

window.addEventListener('load', () => start(), false)
window.addEventListener('load', () => setup_scanner(), false)

async function setup_scanner() {
    const scanPreviewElem = document.getElementById('scan-preview')

    // Debug feature: if an URL fragment is present (#some-voucher-id), then clicking
    // on the video preview will trigger a process of the code defined by the fragment

    scanPreviewElem.addEventListener("click", () => {
        const url_code = window.location.hash.substring(1)
        if (url_code) {
            process_code(CODE_READER, controls, url_code)
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

    CODE_READER = new ZXingBrowser.BrowserQRCodeReader()
    CODE_READER.timeBetweenScansMillis = 1000

    // passing a null deviceID forces the "environment" facingMode
    // https://developer.mozilla.org/en-US/docs/Web/API/MediaTrackConstraints/facingMode
    // https://github.com/zxing-js/library/blob/master/src/browser/BrowserCodeReader.ts#L316
    const controls = await CODE_READER.decodeFromVideoDevice(null, scanPreviewElem, decode_callback)
}

async function decode_callback(result, err, controls) {
    // TODO: handle error
    if (result) {
        await process_code(CODE_READER, controls, result.text)
    }
}

function asyncWait(delay) {
    return new Promise(resolve => setTimeout(resolve, delay));
}

async function process_code(codeReader, controls, code) {
    await process_action(STATE.next_actions.scan, code)
    if (STATE.voucher) {
        controls.stop()
        await asyncWait(5000)
        const options = {}
        options.method = "GET"
        await query("/api/auth/" + STATE.user.id, options)
        const scanPreviewElem = document.getElementById('scan-preview')
        await codeReader.decodeFromVideoDevice(null, scanPreviewElem, decode_callback)
    }
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

    const scan = document.getElementById('scan')
    set_hidden(scan, Boolean(STATE.voucher))

    const history = document.getElementById('history')
    set_visible(history, Boolean(STATE.voucher))

    if (STATE.voucher) {
        const voucher = STATE.voucher

        const voucherTitle = document.getElementById("voucher-id")
        voucherTitle.textContent = voucher.id

        const voucherExpire = document.getElementById("voucher-expire")
        voucherExpire.textContent = voucher.expiration_date

        const voucherValue = document.getElementById("voucher-value")
        voucherValue.textContent = voucher.value + " $"
    }

    const voucher = document.getElementById('voucher')
    set_visible(voucher, Boolean(STATE.voucher))

    const message = document.getElementById('message')
    set_message(message, STATE.message_main)
    set_visible(message, Boolean(STATE.message_main))

    const detail = document.getElementById('detail')
    set_message(detail, STATE.message_detail)
    set_visible(detail, Boolean(STATE.message_detail))

    const action = document.getElementById('action')
    action_button = STATE.next_actions ? STATE.next_actions.button : null
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

function set_hidden(el, hidden) {
    if (hidden) {
      el.classList.add("hidden")
    }
    else {
      el.classList.remove("hidden")
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
