// Get Copyright Information

import { currentDomain } from "./env"

export function getCopyright(domain: String) {
    const date = new Date()
    return "© " + date.getFullYear() + ", " + domain + ". All rights reserved."
}

export function getCopyrightNow() {
    return getCopyright(currentDomain.value)
}