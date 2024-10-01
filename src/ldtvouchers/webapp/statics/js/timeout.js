const t0 = window.performance.now()

function isDebug() {
    const meta = document.querySelector("meta[name=debug]")
    return meta && meta.content === "True"
}

function updateProgress(){
    const el = document.getElementById("timeout-progress")
    const t = window.performance.now()
    el.value = t - t0

    if (el.value < el.max) {
        window.requestAnimationFrame(updateProgress)
        return
    }

    url = document.getElementById("timeout-script").getAttribute("data-timeout-url")
    if (isDebug()) {
        console.log("DEBUG: would move to " + url)
    } else {
        window.location.href = url
    }
}

updateProgress()