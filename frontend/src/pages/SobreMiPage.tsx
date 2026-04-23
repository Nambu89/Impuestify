/**
 * Pagina "Sobre mi" — historia y motivacion del fundador.
 *
 * Separada de la landing porque cuenta contexto personal (por que
 * existe la herramienta, quien la hace, con que fin) que no debe
 * saturar la home.
 */
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useSEO } from '../hooks/useSEO';
import Header from '../components/Header';
import './SobreMiPage.css';

export default function SobreMiPage() {
    useSEO({
        title: 'Sobre mí — Impuestify',
        description: 'Quién hay detrás de Impuestify, por qué existe la herramienta y con qué fin. Fernando Prada, fundador.',
        canonical: '/sobre-mi',
    });

    return (
        <div className="sobre-mi-page">
            <Header />

            <main className="sobre-mi-main">
                <div className="sobre-mi-container">
                    <Link to="/" className="sobre-mi-back">
                        <ArrowLeft size={16} aria-hidden="true" /> Volver a inicio
                    </Link>

                    <h1 className="sobre-mi-title">Sobre mí</h1>
                    <p className="sobre-mi-subtitle">
                        Fernando Prada · fundador de Impuestify
                    </p>

                    <article className="sobre-mi-prose">
                        <h2>De dónde viene Impuestify</h2>

                        <p>
                            Impuestify empezó porque la fiscalidad española es demasiado
                            complicada para cualquiera: da igual que seas pyme, asalariado,
                            funcionario o creador de contenido. La información está repartida
                            entre la AEAT, el BOE, las cuatro Diputaciones Forales y los
                            boletines autonómicos, y nadie tiene tiempo ni ganas de juntarla
                            por su cuenta.
                        </p>

                        <p>
                            Probé los asistentes de IA genéricos y la sensación era siempre
                            la misma: respuestas que suenan bien, pero que se inventan la
                            mitad de la ley. Los RAG comerciales no están entrenados con
                            fiscalidad española; mezclan normativa de otros países, confunden
                            tramos y se saltan los forales como si no existieran.
                        </p>

                        <p>
                            Así que lo monté yo. La idea era coger los documentos oficiales
                            españoles de verdad (hoy hay más de 460 entre AEAT, BOE y las
                            cuatro Diputaciones Forales), indexarlos, y hacer que el
                            asistente citase el artículo concreto de la ley en cada respuesta.
                            Las herramientas que hay dentro no son aleatorias: escuché qué
                            pedía la gente y construí lo que más demanda tenía.
                        </p>

                        <p>
                            Hay un motivo personal detrás. Me cansé de recibir requerimientos
                            de Hacienda y no entender ni la mitad de lo que ponía, y de que
                            la única salida fuera pagar a un abogado para que me tradujera
                            un folio de dos páginas. De ahí salió DefensIA: subes el
                            requerimiento, el sistema lee el documento y redacta el borrador
                            del recurso, para que al menos puedas ir a tu asesor sabiendo de
                            qué va.
                        </p>

                        <p>
                            El fin es ese: que cualquiera que no sea profesional pueda
                            entender su propia fiscalidad, sin carrera de derecho tributario
                            y sin pagar 200 euros al mes a una gestoría que muchas veces
                            tampoco se lo explica.
                        </p>

                        <p className="sobre-mi-signature">— Fernando Prada, fundador.</p>
                    </article>

                    <div className="sobre-mi-cta">
                        <p>
                            ¿Te interesa hablar o tienes una propuesta? Escríbeme a{' '}
                            <a href="mailto:fernando.prada@proton.me">fernando.prada@proton.me</a>.
                        </p>
                    </div>
                </div>
            </main>
        </div>
    );
}
