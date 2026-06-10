/* Figure Preview on Click */

export function setupLightbox() {
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement

    if (!(target instanceof HTMLImageElement)) return

    const figure = target.closest('figure')
    if (!figure) return

    e.preventDefault()
    e.stopPropagation()

    const overlay = document.createElement('div')
    overlay.className = 'lightbox-overlay'

    const content = document.createElement('div')
    content.className = 'lightbox-content'

    const img = document.createElement('img')
    img.src = target.src
    img.alt = target.alt
    img.className = 'lightbox-image'

    content.appendChild(img)

    const caption = figure.querySelector('figcaption')
    if (caption) {
      const captionClone = caption.cloneNode(true) as HTMLElement
      captionClone.classList.add('lightbox-caption')
      content.appendChild(captionClone)
    }

    overlay.appendChild(content)
    document.body.appendChild(overlay)

    const close = () => {
      overlay.remove()
      document.removeEventListener('keydown', escHandler)
    }

    const escHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }

    overlay.addEventListener('click', close)

    // content.addEventListener('click', (e) => {
    //   e.stopPropagation()
    // })

    document.addEventListener('keydown', escHandler)
  })
}