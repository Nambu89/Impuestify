import './InteractiveSpainMap.css'

export default function InteractiveSpainMap() {
    return (
        <div className="spain-map-container">
            <img
                src="/images/hero-spain-3d.webp"
                alt="Mapa de España"
                className="spain-map-image"
                width={1330}
                height={742}
                loading="lazy"
                decoding="async"
                fetchPriority="low"
            />
        </div>
    )
}
