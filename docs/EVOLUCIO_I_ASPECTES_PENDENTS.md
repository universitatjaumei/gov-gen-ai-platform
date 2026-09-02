### Gov Gen AI Platform · Evolució i aspectes pendents

# Evolució i aspectes pendents

*Reunions amb la Unitat d’Anàlisi i desenvolupament · actualitzat el 2 set 2026 · preparat sobre el codi real del repositori*

Desenvolupament va portar tres propostes: fer servir bases vectorials incrustades en xatbots de corpus estable, obrir la plataforma perquè agents externs registren la seua activitat i utilitzen funcionailtats com l'anonimització, i que les seccions web d'actualització permanent (jornades, esdeveniments) alimenten el seu xatbot sense curació manual. Les tres apunten a preocupacions reals, i dues es convertixen directament en blocs de treball. La primera s'ajorna —no per la idea, sinó perquè Postgres està al sistema per moltes més coses que els vectors— i queda com a opció oberta sense cost. La segona és estratègica i encaixa: la meitat de les peces ja estan construïdes. I en la tercera hi ha una: la ingesta automàtica ja existix i corre al scheduler, encara que no es veja des de la interfície; el que falta és tancar-ne el cicle de vida i que els apartats siguen paràmetres que configura qui cura, no res fixat al codi. Els dos paquets de treball ja estan planificats pas a pas.   
S’ha plantejat també una una quarta qüestió, sobre l'arquitectura dels xatbots: si crear-ne un genera codi dins del runtime del producte. No ho fa —és una fila de configuració que interpreta un motor únic—, i de l'alternativa que proposava el correu (una extensió de LangGraph a nivell d'API) ix una proposta que mereix reunió pròpia: que tercers implementen agents dins i fora del sistema via API. I s'hi afig ara una cinquena qüestió, relacionada amb el pilot que ja està en marxa: el SSO institucional, i què passa amb els comptes de persona mentre no hi siga.

- **1 · Bases vectorials incrustades** — *Ajornat, amb la porta oberta.* Postgres continuaria sent necessari per a tot la resta, i la recuperació híbrida porta llindars calibrats que caldria refer. A més el corpus encara es mou. L'opció queda disponible sense pagar res hui: el retriever ja s'injecta darrere d'un protocol.  
- **2 · Registre d'activitat i serveis cap a fora** — *Recomanat.* La preocupació per l'escalabilitat té bona part de resposta ja al codi: el monolit està partit per dins. I la proposta encaixa amb l'arquitectura i amb l'AI Act. Ja està planificada com a paquet de treball propi, per a després del desplegament.  
- **3 · Seccions dinàmiques sense curació manual** — *Ja en marxa; falta tancar el cicle.* L'auto-ingesta de pàgines noves i la reingesta de les canviades ja existixen, amb tests i al scheduler. Falta que l'apartat siga un paràmetre de curació —hui és un lloc sencer— i tancar el cicle: retirada, porta de qualitat i diari. El paquet de treball ja està planificat, en set passos.  
- **4 · ¿Generador de codi o framework?** — *Actualment* crear un xatbot és un `INSERT` de configuració i un motor únic la interpreta en temps de petició. L'«extensió de LangGraph» que proposa el correu és com està construït l'interior; obrir-la a tercers —dins i fora del sistema, via API— es recull com a proposta per a la reunió.  
- **4·bis · Scripts copiats** — Actualment en el mòdul informes es poden generar scripts. El codi d'un script aprovat s'incrusta copiat al bloc de cada plantilla: un bug s'arregla N vegades. Com a consequència del suggeriment es planifica un catàleg de funcions versionades i compartibles — hui per als informes, en el futur per actes activitats o  fases d'expedient. A més, per a futures evolucions es valora la possiblitat d’evolucionar els perfils i les estratègies de l’actual fórmula a través del repositori a un model de plugins. .  
- **5 · SSO institucional i comptes de persona** — *Depén d'un requisit extern.* El SAML està implementat i apagat per configuració. El que el bloqueja no és codi: són les metadades de l'IdP i un nom DNS institucional. Mentrestant no hi ha comptes de persona amb contrasenya —el paquet de treball per a tindre'n ja està planificat— i el pilot funciona amb sis comptes elevats que caldrà baixar.
- **6 · Procediments al costat de la normativa** — *Recomanat: un sol assistent, sense enrutador.* Els assistents del pilot no contesten qüestions de procediment (servei que tramita, terminis, silenci) perquè això no és a la normativa: és al catàleg de procediments, ara en revisió pels serveis. La gent pregunta les dues coses barrejades i sovint no les distingix, així que les fitxes validades entren al mateix corpus com a documents amb el seu propi tipus, i el circuit d'actualització reutilitza la sincronització que ja manté el corpus normatiu. El paquet de treball ja està planificat; el prerequisit és la validació de les fitxes.

---

### Abans d'entrar en detall

## Les tres propostes assenyalen problemes que existixen

Convé dir-ho abans que res, perquè la resta del document entra en el detall tècnic i allí és fàcil perdre de vista el que importa: **les tres aportacions van donar en preocupacions legítimes**, i dues es traduïxen ja en treball planificat. La primera posa el focus en la dependència d'infraestructura, que és la pregunta correcta quan es pensa a desplegar molts xatbots. La segona anticipa una cosa que efectivament passarà —ús d'IA fora de la plataforma, sense ningú registrant-ho— i va arribar abans que fóra un problema. I la tercera va posar nom a un buit real del cicle de vida del contingut, que estava a mig tancar sense que ningú ho haguera notat.

Bona part de les respostes d'ací baix són «això ja està», i això no és cap retret a qui va preguntar: **quasi res d'eixa maquinària es veu des de la interfície** —viu al scheduler, en jobs i en taules—, així que l'única manera de saber-ho era obrir el codi. Que les propostes coincidisquen amb decisions ja preses és, sobretot, un senyal que anem en la mateixa direcció.

### Punt de partida

## Què hi ha ja construït

Fixar l'inventari ajuda a valorar les propostes, perquè la segona no parteix de zero:

- **Servidor MCP complet** (`mcp_server/`): 16 tools i 5 resources per a autoria de plantilles, configuració de xatbots i xat de prova, amb 54 tests. La valoració de `docs/mcp.md` va deixar anotat l'MCP remot com a pas següent quan hi haguera cas d'ús.  
- **PAT amb permisos per rol** (`core/auth/pat/`): tokens de màquina revocables, amb catàleg de permisos i sostre per rol. És la peça d'autenticació que un client extern necessita.  
- **Mòdul d'anonimització operatiu** (`modules/redaccion/services/anonymization/`): detecció de dades personals en text lliure (`detect_spans`) i tabular, polítiques, generació amb Faker, i modes per workspace amb herència. Hui només el consumix el mòdul de redacció.  
- **Registre intern d'interaccions** (`HubInteraction`): captura el que ocorre *dins* de la plataforma. Res no registra hui l'ús d'IA que passa fora.  
- **SSO per SAML implementat i apagat** (`core/auth/saml/`): les quatre rutes, l'alta automàtica de persones en validar l'asserció i el mapatge de grups a rols però falten les dades per valorar-ho.

---

### Qüestió 1

## Vectors incrustats: la intuïció és bona, però l'estalvi es queda curt

La idea de fons —baixar la dependència d'infraestructura d'un xatbot amb un corpus que quasi no canvia— és sensata, i en un altre sistema seria la decisió correcta. El que la complica ací són quatre detalls concrets de com ha acabat muntat este:

- **Llevar els vectors no lleva el servidor.** Postgres guarda també els documents, les interaccions, els jobs d'ingesta, el vocabulari versionat i la tinença per organització. Un xatbot amb LanceDB o Chroma incrustat continuaria necessitant la mateixa base de dades per a tot la resta, així que el resultat seria afegir un magatzem més i no retirar-ne cap.  
- **La recuperació ha acabat sent bastant més que «veïns més pròxims».** És híbrida — vector més `tsvector` com a pont bilingüe valencià/castellà —, filtra per una taxonomia que viu en taules versionades, i té llindars calibrats per mesura amb consultes reals (0,60 a Normativa, 0,35 a Gerència). Una base incrustada obligaria a reimplementar i *recalibrar* tot això en un segon camí de codi, amb la seua segona bateria de tests.  
- **Tensiona l'invariant «reclassificar \= un UPDATE».** El vocabulari està pendent de validació per Secretaria General i canviarà. Amb N magatzems incrustats repartits per xatbot, cada canvi d'etiqueta tocaria N fitxers en compte d'una taula.  
- **El «corpus estable» encara no ho és del tot.** El corpus complet es va reingerir als quatre assistents fa uns dies, hi ha 35 documents pendents de confirmació i la curació continua activa. I a l'escala actual — 313 fitxes, 308 pàgines — pgvector a la màquina va sobrat, així que ara mateix no hi ha cap mesura de rendiment que empenya en esta direcció. Pot canviar: si apareix, la conversa es reobri amb dades.

La porta queda oberta a propòsit: el retriever ja s'injecta per `Depends` darrere d'un protocol. Si algun dia un desplegament ho justifica — un edge node mínim sense Postgres —, afegir un backend incrustat és additiu i no exigix migrar res. És a dir: no cal decidir-ho hui per a poder fer-ho demà, i per això proposem esperar en compte de tancar l'opció.

---

### Qüestió 2

## L’aplicació com a registre d’IA d’altres eines. 

**L’aplicació no està connstuida de forma del tot nonolítica.** .Està partit per dins precisament per a poder separar-se: dos `DeclarativeBase` (configuració/operacional), `DEPLOY_MODE` amb classificació de routers cloud/edge, `ConfigProvider`, i la prohibició d'imports edge→cloud amb guardarrails en tests. Eixa frontera existix i es vigila en cada commit.

**A més, la proposta d’obrir-la a altres usos és estratègica i encaixa bé.** L'ús d'IA a la institució passarà cada vegada més *fora* de la plataforma — Claude Cowork, Copilot, agents de tercers — i hui res no ho registra. Un registre central d'activitat d'IA és exactament el que l'AI Act demana als responsables del desplegament (conservació de logs, arts. 12 i 26\) i el que un registre d'activitats de tractament del RGPD (art. 30\) agraïx. I l'anonimització com a servei evita que cada eina externa resolga les dades personals pel seu compte, pitjor.

Una delimitació important: això és **registre de governança, no traçat tècnic**. El traçat token a token ja el cobrix Langfuse dins de la plataforma; el que falta és l'esdeveniment de nivell legal — qui va usar quin agent, amb quina finalitat, sobre quines categories de dades. No cal reconstruir Langfuse.

---

### Proposta

## La proposta del registre: exposar el que ja hi ha, amb dues superfícies

No és una re-arquitectura. És un paquet de sis passos, **ja planificat**, que exposa peces existents amb REST per a qualsevol client i MCP com a façana per a agents:

| Pas | Entregable | Notes de disseny |
| :---- | :---- | :---- |
| 1 | Contracte `ActividadIAEvent` i taula `hub_actividad_ia` (operacional, edge) | Esdeveniment de governança: actor, organització, eina externa, finalitat, model, categories de dades declarades, marques de temps. **Metadades sí, contingut no**, garantit per contracte (`extra="forbid"`): el registre no pot convertir-se en un segon lloc on viuen les dades personals. Taula nova — no sobrecarregar `HubInteraction`. |
| 2 | Endpoint `POST /api/v1/actividad` i els dos permisos nous | Permisos `actividad:write` i `anonimizacion:use` al catàleg PAT. L'organització de l'esdeveniment es deriva del propietari del token, mai del contingut de la petició. |
| 3 | Anonimització com a servei: `/anonimizacion/spans` i `/anonimizacion/replace` | Exposa `PiiDetector.detect_spans` i l'anonimitzador sobre text lliure. Edge per definició; el text no toca logs ni base de dades, amb test que ho vigila. |
| 4 | MCP remot (HTTP streamable) com a façana fina | Tools `registrar_actividad`, `detectar_pii`, `anonimizar_texto` al mateix paquet `mcp_server/`, amb el token de cada client propagat per petició. És l'«opció B» que `docs/mcp.md` va deixar anotada; este és el cas d'ús que la justifica. |
| 5 | Lectura i exportació del registre | `GET /api/v1/actividad` paginat amb filtres i exportació CSV, per a sessió d'administració, acotat a l'organització del principal. |
| 6 | Vista al panell d'administració i la guia del registre | Taula amb filtres i i18n; documentació del contracte camp a camp amb el mapatge a OTel GenAI i la guia d'alta d'un agent extern. |

**Seqüència:** no interferix amb el treball en curs. De fet convé executar-lo *després* del desplegament: un MCP remot només existix de veritat amb el servidor accessible des de fora.

---

### Qüestió 3

## Seccions dinàmiques per al módul de curació: la ingesta automàtica ja existix; el que falta és la resta del cicle

Dues de les tres peces necessàries ja estàn fetes, amb tests i corrent al scheduler que arranca amb l'aplicació, tot i que —**no hi ha res a la interfície que ho conte**, i des de fora un xatbot que s'actualitza sol és indistinguible d'un que no\_:

- **Rastreig periòdic per apartat.** El rastrejador ja treballa amb «un lloc per apartat»: un `HubWebSite` amb `url_regex_filter` acota `/jornades` o `/esdeveniments` i té la seua pròpia cadència (`crawl_interval_hours`). El diff per `content_hash` distingix noves, canviades i desaparegudes.  
- **Auto-ingesta de pàgines noves.** La regla de selecció (`HubCorpusSelection`) té una columna `auto_ingest_new` — activada per defecte — i el job programat la consumix: una pàgina nova que casa la regla entra sola al xatbot (`quality_job.py`).  
- **Reingesta automàtica del que ha canviat.** Una pàgina ja ingerida el contingut de la qual canvia al portal es reingerix sola, amb l'avís `content_updated` per a poder revisar què ha canviat.

El principi que sosté això — i que convé conservar — és **«curació una vegada, automatització després»**: l'apartat i el seu mode els definix un curador després de la primera passada manual (que és on es calibren les trampes del portal real: commutador d'idioma, prefixos duplicats, pàgines que necessiten JavaScript), i dins d'eixe àmbit l'automatització manté. No s'auto-ingerix res que cap persona haja aprovat mai; es manté el que una persona va aprovar una vegada.

## L'apartat ha de ser un paràmetre, no una decisió de codi

Hui un apartat s'expressa **creant un lloc sencer** amb el seu filtre d'URL. És la decisió que es va prendre en el seu moment i tenia bona raó — cada apartat té un responsable distint —, però paga un preu que es nota justament quan els apartats es multipliquen: duplica l'URL arrel, el sitemap, la configuració de cortesia i els criteris de judici; exigix una alta tècnica per apartat; i convertix «afegir l'apartat de beques» en treball de qui administra llocs, en compte de treball de qui cura.

És el mateix raonament que el projecte ja va aplicar al vocabulari del corpus: **el que canviarà mentre algú ho fa servir és dada, no estructura**. Per això la proposta introduïx la **secció** com a entitat configurable dins del procés de curació — amb el seu patró, la seua cadència, el seu mode (manual o automàtic), el seu responsable i els seus criteris propis —, i amb dues regles que la fan barata de mantindre: *nul hereta* (un paràmetre buit a la secció pren el del lloc, la mateixa semàntica que ja fa servir la cascada de configuració) i la pertinença d'una pàgina es *deriva del patró* en compte d'emmagatzemar-se, perquè els patrons s'editen. Un lloc sense seccions continua comportant-se exactament com hui.

No obstant, al ampliar la curació a seccions apareix un risc que hui no existix. El rastreig declara «baixes» les pàgines que ja no apareixen, comparant el que acaba de veure contra les pàgines registrades del lloc sencer. Hui és correcte perquè el lloc és l'apartat. Amb diverses seccions en un mateix apartat,, una passada completa de /esdeveniments veuria només les URL d'esdeveniments i declararia baixa la resta del apartat..

És exactament la lliçó que el corpus normatiu ja té escrita («una càrrega parcial que s'interpretara com a cens retiraria centenars de normes»), així que la primera regla dura de la proposta és que el cens s'acota a l'àmbit realment rastrejat, amb test dedicat i amb una comprovació de recompte abans/després a la verificació final.

A més, falten tres peces del cicle de vida, i ací la proposta va encertar de ple: són buits nostres que ningú no havia mirat des del punt de vista d'un apartat d'esdeveniments. Per a eixe cas, la primera és la que més pesa:

- **La retirada automàtica no existix.** El rastreig marca les pàgines desaparegudes, però retirar-les del corpus només existix com a acció manual del curador: un esdeveniment esborrat del portal continua al corpus responent com si existira. Contingut caducat servit com a vigent és el mode de fallada dominant d'una secció d'esdeveniments.  
- **L'auto-ingesta no té porta de qualitat.** Ingerix qualsevol pàgina nova que case la regla sense consultar les troballes que el mateix job acaba de calcular: una pàgina buida o que necessita JavaScript per a pintar-se entraria al corpus. L'automatització no pot tindre menys criteri que el curador a qui substituïx.  
- **El curador no pot auditar el que l'automatització ha fet.** Els comptadors de cada passada es calculen i es perden. Una automatització que no es pot auditar barata s'apaga al primer ensurt — amb raó.

## La proposta de seccions, en set passos

| Pas | Entregable | Notes de disseny |
| :---- | :---- | :---- |
| 1 | La secció com a dada, i quin paràmetre guanya quan n'hi ha dos | Patró, cadència, mode, responsable i criteris per secció, amb herència del lloc allà on el valor estiga buit. El mode d'una secció nova naix en **manual** a propòsit: no automatitza fins que algú ho diu. |
| 2 | Rastrejar per secció sense que el cens s'emporte la resta del lloc | Cada secció amb el seu rellotge, i la declaració de baixes acotada a l'àmbit rastrejat — la trampa descrita adés, amb el test que la fixa. |
| 3 | Parametritzar seccions dins del procés de curació | Crear i editar seccions des de la interfície, amb **prova del patró abans de guardar** (quantes pàgines ja rastrejades casarien, i una mostra): és el que evita el patró que no casa res, que hui només es descobriria quan la passada següent no ingerix. |
| 4 | Retirada automàtica de les pàgines desaparegudes | Només en seccions automàtiques; les manuals reben avís. Amb **salvaguarda de proporció** (si desapareix més del 30% de l'àmbit en una passada, no es retira res i avisa): un rastreig trencat no pot buidar un corpus. |
| 5 | Porta de qualitat en auto-ingesta i reingesta | Una pàgina amb troballes bloquejants (buida, illegible, necessita JavaScript) no entra: queda com a candidata amb el motiu visible. Resolta la troballa, la passada següent la ingerix sola. En reingesta, la versió bona del corpus es conserva. |
| 6 | Diari de l'automatització a la pantalla de curació | Cada passada persistix el seu àmbit i què va ingerir, reingerir, retirar i bloquejar, i per què; el curador ho veu per lloc i per secció, el més recent damunt. |
| 7 | Un apartat real, parametritzat per qui cura, de punta a punta \+ la guia escrita | Tot per la interfície (si cal SQL a mà, la interfície està incompleta), i el cicle verificat de veritat: nova que entra, canviada que es reingerix, esborrada que es retira, i la resta del lloc intacta. La recepta queda escrita per a l'apartat següent. |

**Seqüència:** independent del desplegament (tot és edge i ja corre en local) i **sense dependre de decidir cap apartat**: quines seccions existisquen és configuració, i les crea qui cura el dia que les necessite. Queda fora a propòsit el corpus normatiu (les seues fonts tenen la seua pròpia porta de validació) i la *caducitat editorial* — l'esdeveniment passat que continua publicat — que és una decisió del propietari del contingut, no del codi (l'últim pas la documenta amb opcions).

---

### Qüestió 4 · Generador de codi vs framework

L’aplicació no crea xatbots  generant codi. Efectivament això seria difícil de mantindre. 

- **Crear un xatbot és una fila de configuració.** L'endpoint de creació (`hub_chatbots_router.py`) fa un `INSERT` a `hub_chatbots`: prompt de sistema, mode de recuperació, llindars de qualitat, quotes, política de llengua, perfil de graf. Tot declaratiu, en base de dades. No s'escriu cap fitxer ni es genera cap artefacte executable.  
- **Un motor únic interpreta eixa configuració en temps de petició.** `GraphFactory` resol la configuració efectiva per la cascada Plataforma→Organització→Xatbot i compon un `CoreGraph` a partir de perfils registrats en un `GraphProfileRegistry` (patró factory \+ strategy, sobre LangGraph). La conseqüència és la contrària de l'escenari temut: **un bug es corregix una vegada al motor i tots els xatbots l'hereten a l'instant**, perquè no existix codi per xatbot que actualitzar.  
- **Els «xicotets canvis particulars» es fan en configuració, no en codi.** Per xatbot s'ajusten prompt, plantilla de resposta, mode de recuperació (vectorial / context llarg / agèntic), llindars, missatges i quotes. Deliberadament: l'usuari objectiu és un administrador no programador, que pot fer-ho sense obrir una PR ni desplegar.

L'alternativa que es proposaja és l'arquitectura interna — i obrir-la és la proposta que mereix la reunió  
L'«extensió de LangGraph a nivell d'API» que es suggerix descriu amb bastant exactitud com està construït l'interior: `agent/public_graphs/` és un mini-framework sobre LangGraph amb un graf genèric (`CoreGraph`), estratègies intercanviables (recuperació, fusió, plantilla, política de llengua) i un registre de perfils amb `register_profile()`. Afegir un tipus d'agent és registrar una factoria, no tocar el motor.

El que no està fet — i és decisió de producte, no d'arquitectura — és exposar eixe punt d'extensió cap a fora. De la suggerència ix una proposta concreta: **que tercers implementen agents dins i fora del sistema via API**, en dues superfícies amb costos molt distints:

- **Fora del sistema — ja planificat.** Agents externs que consumixen els serveis de valor de la plataforma via REST i MCP remot: registre d'activitat d'IA, detecció i anonimització de dades personals, amb PAT i permisos. És exactament el paquet del registre descrit adés; esta meitat de la proposta no cal ni decidir-la, només confirmar-la.  
- **Dins del sistema — proposta nova, a valorar.** Obrir el `GraphProfileRegistry` com a contracte públic d'extensió, en dues variants no excloents: (a) *perfils aportats* — un equip extern entrega un perfil de graf (paquet Python contra el contracte d'estratègies) que hereta de sèrie multitinença, quotes, llindars, política de llengua, traçat i avaluació; i (b) *agents remots orquestrats* — el xatbot declara un endpoint extern i el CoreGraph li delega la generació, mantenint dins la recuperació, les portes de qualitat i el registre. La (b) no executa codi alié a l'edge node, i per això és la primera candidata.

Els costos que cal posar damunt la taula abans de decidir: codi de tercers executant-se prop de dades internes amb qüestions de de seguretat i de compliment, decisiva en la variant a), versionat i estabilitat d'un contracte públic d'extensió — hui el registre canvia quan el projecte ho necessita, amb contracte hi ha deprecacions —, i suport. Res d'això no exigix refer res: el registre és exactament la costura on s'obriria. La recomanació és tractar-ho com a **paquet de treball propi, posterior al del registre d'activitat**, perquè eixe ja construïx la meitat dels seus prerequisits (autenticació de màquina, registre d'activitat, MCP remot).

## On el suggeriment sí encerta és en els scripts dels informes. En eixe modul, nodes del graf es compartixen per construcció: totes les plantilles d'informe passen pels mateixos nodes del DraftingCoreGraph, i tots els xatbots pel mateix CoreGraph. Però el codi d'un script aprovat (només està previst al mòdul de informes) s'incrusta copiat dins del bloc de cada plantilla (scripts\_router.py: options={"code": …, "approved": true}): dues plantilles que necessiten la mateixa extracció són dues propostes, dues aprovacions i dues còpies, i un bug en un script usat per N plantilles s'arregla N vegades. La cua d'aprovació (HubScriptProposal) apunta a una plantilla concreta i mor en aprovar-se: és una cua, no un catàleg. Ací sí que hi havia «generador», i es corregix.

La resposta és un **catàleg de funcions**, ja planificat pas a pas, que convertix els scripts en peces reutilitzables:

- **Catàleg versionat amb contracte declarat.** Cada funció declara el seu contracte d'entrada (fitxers i paràmetres tipats, dels quals la interfície deriva el formulari) i d'eixida, i cada versió aprovada és **immutable**: corregir és publicar una versió nova. L'entrada es valida contra el contracte *abans* d'arribar al sandbox: si un ERP canvia de format, l'error és «l'entrada no complix el contracte», no un traceback.  
- **Referència en lloc de còpia, amb ancoratge.** El bloc d'una plantilla referencia `funció@versió`; publicar la v2 **no canvia cap plantilla existent** — cada consumidor adopta la correcció quan decidix. És el que convertix «arreglar el bug una vegada» en cert sense alterar en silenci informes ja aprovats.  
- **Compartida entre organitzacions.** Una funció naix de la seua organització; **promocionar-la a plataforma requerix aprovació del superadministrador**, i llavors qualsevol organització la referencia (cas motor: l'explotació d'un ERP comú). Es compartix codi i contracte, **mai dades**, i la cadena de seguretat no es relaxa: auditoria AST \+ sandbox \+ aprovació humana en tota alta i tota versió.  
- **Consumible per API.** `POST /api/v1/funcions/{id}/run` amb token de màquina i scope propi, execució al sandbox i rastre al registre d'activitat — per això este pas va després del paquet del registre, que construïx eixes peces.

## Dos orígens per a una funció: el codi es queda on l'escriu qui el manté

La segona observació de desenvolupament —que gestionar eixe codi dins de la ferramenta és reinventar la roda, que ha d'estar en mans de qui el definix, versionat, testejat i mantés contra una API declarada, amb control semàntic de versions— **té raó per a l'autor desenvolupador**. Per a un equip amb repositori, CI i pip, guardar codi en files de base de dades amb versionat propi és estrictament pitjor que git. El que la pregunta no veu és **l'altre autor**: l'informador o l'administrador sense entorn de desenvolupament, que descriu una extracció, rep el codi proposat per la IA, el veu auditat i provat en sandbox amb dades anonimitzades, i l'aprova. Eixe autor no té repositori ni desplegament, i el seu codi corre vora dades que no pot traure. El disseny del catàleg s'ha revisat (2 de setembre) per a servir als dos sense triar:

| | Origen **autoservici** | Origen **empaquetat** |
| :---- | :---- | :---- |
| Nivell de la Instrucció 02/2026 | **Nivell 2**, desenvolupament ciutadà compartit al servici (i nivell 3 si es promociona) | **Nivell 3**, desenvolupament corporatiu |
| Autor | La persona referent de desenvolupament ciutadà: porta un script que ja usava al seu equip, o el construïx amb la IA dins de la plataforma | Equip de desenvolupament (UADTI), al seu repositori, amb la seua CI |
| On viu el codi | Al catàleg | En un paquet Python instal·lat al desplegament, descobert per *entry point* |
| Com entra | **Registre** = declaració responsable + auditoria AST + prova en sandbox, automàtics → **ús immediat** al servici → revisió posterior o per mostreig | `pip install` per qui opera; la plataforma el registra a l'arrancada i en valida el contracte |
| On corre | Sandbox | Al procés del servidor: la confiança és de qui l'instal·la, com en un plugin |
| Versionat | Ordinal del catàleg, versió aprovada immutable | Semver del paquet; el catàleg registra cada versió instal·lada amb el hash de la font |
| Ancoratge d'una plantilla | Versió exacta, **per construcció** | Mateix *major* de semver, **per contracte**; un *major* distint falla en alt |
| Àmbit | Naix a la seua organització; promoció a plataforma pel superadministrador | Plataforma des del principi: l'instal·la qui opera, no una organització |

Vosaltres conserveu git i el control semàntic de versions; nosaltres conservem l'autoservici; i el catàleg deixa de ser un gestor de paquets casolà. La frontera de confiança es diu sense embuts: el codi empaquetat no passa pel sandbox, i per això naix com a plataforma i entra per desplegament i no per formulari.

## El catàleg com a canal del nivell 2 de la Instrucció 02/2026

El catàleg no està pensat per a desenvolupadors professionals: està pensat per a **governar el desenvolupament ciutadà** que regula la *Instrucció 02/2026 del Delegat per a l'Estratègia Digital i la IA* (marc de *citizen development* governat i prevenció del *Shadow IT*). La Instrucció diu que la diferència entre automatització intel·ligent i caos «no rau en qui escriu el codi, sinó en com es governa», i fixa tres nivells amb control proporcional a l'abast. El **nivell 1** (ús personal: macros, scripts locals, Colab) és lliure i **queda fora de la plataforma**. **La plataforma entra al nivell 2**: quan una persona referent vol compartir la seua solució amb el servici, la Instrucció exigix declaració responsable i registre «pels canals que indique la UADTI», ús immediat i revisió posterior o per mostreig, **mai aprovació prèvia bloquejant**. Registrar una funció al catàleg **és** eixe acte. I el **nivell 3** (abast superior al servici, valor institucional) és el pas a desenvolupament corporatiu: la promoció a plataforma, o directament l'origen empaquetat.

Contrastar el disseny amb la Instrucció ha fet canviar quatre coses del bloc de treball, i convé dir-les perquè són justament el que la UADTI té encomanat:

| La Instrucció diu | El catàleg ho fa així |
| :---- | :---- |
| §5 nivell 2 i §8: declaració responsable i registre; ús immediat; **revisió posterior o per mostreig, mai com a condició prèvia** | Registrar = declaració responsable (finalitat i categories de dades) + auditoria AST sense troballes crítiques + prova en sandbox, **automàtics**; la versió queda registrada i usable al moment. **S'ha retirat l'aprovació humana prèvia** que el disseny inicial exigia a tota funció: era el control desproporcionat que la Instrucció diu que empenta cap al *Shadow IT*. |
| §8.4: la revisió posterior pot derivar en correccions, reclassificació o suspensió | Cua de revisió posterior amb **mostra aleatòria**, resultat (conforme, correccions, reclassificada) i **suspensió amb motiu**: una versió suspesa no s'executa i el bloc que la referencia falla en alt dient per què. Suspén qui revisa; retira qui escriu (§9, dues responsabilitats). |
| §4 i §5 nivell 3: valor d'informació superior al servici → desenvolupament corporatiu | La promoció a plataforma és **l'única aprovació prèvia** del bloc, amb valoració escrita del superadministrador; la revisió pot marcar una funció com a candidata a nivell 3, i la plataforma només **senyala**, no decidix. |
| §8.1: la persona referent construïx la solució al seu equip (nivell 1) | El registre **accepta codi escrit fora**, no sols el proposat per la IA: el cas majoritari de la Instrucció és un script que ja funcionava. Els dos camins passen per la mateixa auditoria i el mateix sandbox; consta l'autoria. |
| §6 regla 1: ecosistema autoritzat (la caixa d'eines) definit a les Guies Operatives Tècniques | **L'auditor AST és la caixa d'eines**: mòduls permesos, prohibicions, rutes. Les seues regles es publiquen des del codi i **es contrasten amb les Guies**: si divergixen, cada pas de nivell 1 a 2 és una reescriptura. Mantindre-les és paper de la UADTI. |
| §5 nivell 2: el registre protegix del *bus factor* | Catàleg amb versions immutables, contracte declarat, autoria i qui usa què: si la persona referent marxa, les funcions del servici estan inventariades i recuperables. |
| Annex III.3: revisió posterior amb anàlisi estàtica i eines d'IA | Auditoria AST amb tres nivells (segura, avís, crítica) a l'entrada; el manifest d'execució i el registre d'activitat com a rastre per a la revisió. |
| OIATI: tractament de dades personals | Dades de prova anonimitzades abans del sandbox; detecció de PII i anonimització abans del model; la declaració de categories de dades és el que l'OIATI llig. |

**Una diferència que no s'ha d'amagar.** La regla 2 de la Instrucció diu que l'automatització s'executa a l'equip de la persona, amb les seues credencials, i que no es guarden dades fora de l'entorn local. La plataforma fa el contrari a propòsit: **el codi va a les dades**, al node institucional, i els fitxers es guarden a l'emmagatzematge de la institució. És un règim **més** controlat que el de la Instrucció (cap dada al portàtil de ningú, cap credencial dins d'un script), però és un règim distint: la Instrucció fixa el marc per a l'automatització local, i la plataforma és l'ecosistema autoritzat per a quan el tractament ha de passar vora dades que no han d'eixir. Que això siga així és una decisió de la UADTI i de l'OIATI, no una interpretació nostra, i és bo que la prenguen ells.

I ací és on el correu de desenvolupament té la resposta més curta: la Instrucció encomana a la UADTI **definir la caixa d'eines, gestionar el registre i fer la revisió posterior**. El catàleg no vos lleva res d'això: és el lloc des d'on fer-ho sobre codi que, si no, circularia per correu.

## Per què centralitzar-ho a la plataforma encara que el codi visca fora

El valor de la ferramenta enfront de Claude Code no està en escriure el codi —ahí Claude Code guanya per a un desenvolupador— sinó en tot el que passa **al voltant** d'una execució i que un repositori no registra. Git versiona codi; la plataforma versiona **decisions i execucions**. Concretament, i açò és igual per als dos orígens:

- **Una sola cua de revisió i aprovació**, amb qui va aprovar què i quan. Un script en un repositori té una PR aprovada per un desenvolupador; una funció del catàleg té una aprovació de qui respon del contingut de l'informe, que no és la mateixa persona ni el mateix criteri.
- **El manifest d'execució (`RunManifest`) de cada informe** registra quina funció, quina versió exacta i quin hash del codi va córrer sobre quines entrades. Un informe aprovat fa sis mesos es pot explicar peça a peça. Un script al repositori d'un equip no deixa rastre de en quin informe es va usar ni amb quina versió.
- **Traçabilitat creuada amb el registre d'activitat**: qui va executar quina funció, des de quina ferramenta, amb quina finalitat, sense les dades. És el que exigix un registre de tractaments i el que un desplegament aïllat no pot reconstruir.
- **Un contracte d'entrada i eixida declarat en un sol lloc i validat abans d'executar.** D'eixe contracte ix el formulari de la interfície, la validació de l'API externa i, més avant, l'acció d'una fase d'expedient. Si un ERP canvia de format, l'error és «l'entrada no complix el contracte» a la pantalla de qui genera l'informe, no una traça de pandas en un log.
- **El codi va a les dades, no les dades al codi.** L'execució passa al node vora les dades, amb l'anonimització abans del model. Un informador no pot traure un fitxer de nòmines per a passar-li'l a un script en el seu portàtil, i no hauria de poder.
- **Inventari i frontera d'organització**: quines funcions existixen, qui les usa i en quantes plantilles, quina versió està anclada on, què està retirat, i quina organització veu quina funció. Amb el codi repartit en repositoris, eixa pregunta no té on contestar-se.

Una funció empaquetada hereta tot això el dia que s'instal·la, sense escriure res més que el descriptor del seu contracte. Eixa és la resposta curta a «quin valor afegit té fer-ho a la ferramenta»: cap per al codi, tot per a la seua governança.

I el catàleg és una peça **compartida amb el futur mòdul d'expedients**. La convergència assenyalada l'1 de setembre — baremació, resolució provisional i resolució definitiva com a *fases d'un expedient*, cadascuna amb la seua plantilla — va destapar que el disseny esbossat per a eixe mòdul hauria construït **un segon motor d'execució de codi** paral·lel al sandbox, l'auditoria i l'aprovació existents (guardava el codi executat dins de cada acció). El disseny es va corregir el mateix dia: les accions d'una fase referencien `plantilla@versió` (l'execució *és* un workspace del motor de redacció, amb les seues portes de revisió humana) i `funció@versió` del catàleg, mai codi incrustat. El gestor d'expedients institucional — que no usa IA — seguix sent la font de veritat del procediment i pot invocar per API l'execució d'una fase amb IA. **Un sol motor, dos productes.**

## Estratègies com a endolls, perfils com a col·leccions — i el model de plugins

Per a la part de la proposta que sí que és codi de motor — «alguns agents necessitaran funcionalitats que els actuals no tenen», com l'anonimització —, convé fixar el vocabulari, perquè és exactament l'extensió de LangGraph que el correu demanava:

- **Una estratègia és un endoll.** El `CoreGraph` no sap com es recupera, es fusiona, es redacta ni es resol la llengua: compon cinc protocols tipats (recuperació, fusió, plantilla de resposta, política de llengua, bucle agèntic). Una funcionalitat nova de node és una implementació nova d'un d'eixos protocols — l'exemple de l'anonimització són \~50 línies que criden el servici que ja existix — o un endoll nou si és un eix que no existia.  
- **Un perfil és una col·lecció d'estratègies.** Un «tipus d'agent» distint dels xatbots de normativa és un perfil nou al `GraphProfileRegistry`: una composició concreta d'estratègies, seleccionable per configuració. Ja hi ha un test de contracte que exigix a tot perfil registrat compilar i executar, i els perfils sense configurar fallen en alt en lloc de recuperar buit en silenci.  
- **El registre és el punt on tot açò s'obri**, quan calga: registrar un perfil és una crida a `register_profile()`, no tocar el motor.

Sobre **com entra eixe codi**, hi ha dos models seriosos — i un tercer que no ho és: donar d'alta codi de motor per la interfície en runtime queda descartat, perquè el codi de motor no cap al sandbox i sense sandbox cap auditor estàtic el fa segur. Els dos seriosos: **canvis al repositori** (com fins ara) i **plugins de desplegament** — paquets Python que s'auto-registren via *entry points* (`govgenai.graph_profiles`, `govgenai.strategies`: valen per a perfils *i* per a estratègies) i que qui opera el desplegament instal·la amb pip, el model de pytest o Airflow: el codi entra pel desplegament, revisat i versionat, no per un formulari.

## Ampliar per repositori o per plugins: pros i contres

| Via | A favor | En contra |
| :---- | :---- | :---- |
| Repositori (el model actual) | Un sol lloc de veritat; els protocols d'estratègia poden evolucionar quan el projecte ho necessita, sense deprecacions; CI i el test de contracte cobrixen *tots* els perfils en cada commit; la revisió de codi és el flux natural de PR; cap gestió de compatibilitat de versions entre motor i extensions. | Tot perfil nou passa per l'equip del repositori — coll de botella si un tercer vol desenvolupar pel seu compte; acobla el ritme dels tercers al del projecte; l'única alternativa que els queda és el fork, que fragmenta. |
| Plugins de desplegament | Un tercer desenvolupa i manté el seu perfil sense tocar el repositori ni esperar release; cada desplegament instal·la només el que usa (rellevant en edge); habilita ecosistema — un ajuntament o una altra universitat publica el seu perfil; frontera de responsabilitat clara: paquet versionat, instal·lat per qui opera. | Exigix **congelar els protocols d'estratègia com a contracte públic** amb deprecacions — un cost permanent que hui no es paga; el que no està a CI no el cobrix el test de contracte: un plugin trencat es descobrix al desplegament; el codi del plugin corre **sense sandbox** dins del procés del servidor — la confiança es desplaça a qui l'instal·la; i cal compatibilitzar dependències pesades (torch, langgraph) entre motor i plugin. |

**Recomanació:** repositori mentre els perfils els escriga l'equip — hui n'hi ha un d'operatiu i cap tercer esperant. El mecanisme d'entry points s'afig el dia que existisca el primer tercer real amb un perfil que mantindre: és **additiu** (el registre ja existix i no canvia) i no cal decidir-ho hui. El que sí que convé des de hui és no deixar que els protocols d'estratègia acumulen dependències accidentals, que és exactament cap on empeny el test de contracte de perfils.

---

### Qüestió 5 · del pilot, no de desenvolupament

## SSO institucional: el que falta no és codi

El SSO per SAML **està implementat**: les quatre rutes (`/auth/saml/login`, `/acs`, `/metadata`, `/logout`), l'alta automàtica de la persona quan es valida l'asserció, i la derivació del rol a partir dels grups que declara l'IdP. Està apagat per configuració (`SAML_ENABLED=false`) perquè li falten dades que no depenen de nosaltres.

La petició completa a Informàtica està redactada a banda. Ací interessa el que afecta la planificació, que són dues coses: **un requisit extern que va davant de tot**, i **què passa amb els comptes mentre no hi haja SSO**.

**El requisit que va davant: un nom DNS institucional.** L'identificador del proveïdor de servei (*EntityID*) i l'URL del punt de retorn (ACS) es construïxen sobre el nom de l'amfitrió, i són precisament les dues dades que l'IdP registra. Canviar-los després no és una redirecció: obliga a registrar el servei de nou.

El prototip respon hui en una adreça derivada de la seua IP (`34-175-38-129.sslip.io`), i és molt probable que un IdP institucional **no accepte registrar un proveïdor de servei en `sslip.io`**, que és un servei de tercers que resol qualsevol IP. Si el subdomini ha d'existir, millor que existisca *abans* del registre.

Del que ens han de donar, tres coses són les que solen quedar a mitges:

- **Els noms literals dels atributs.** Cada IdP els diu d'una manera. Els nostres valors per omissió són `mail`, `displayName` i `groups`, però molts IdP institucionals els envien com a OID (`urn:oid:…`). Si difereixen, s'ajusten per variable d'entorn i no cal tocar codi. **El correu és obligatori**: sense ell l'ACS rebutja l'asserció, perquè és la clau amb què s'identifica la persona.  
- **Els grups que donen cada rol, amb el seu valor exacte.** Es configuren en un mapatge de grup a rol; qui no casa cap grup entra amb el rol per defecte. Un grup mal escrit *no dóna error*: dóna una persona amb el rol mínim que no entén per què no veu res.  
- **Si exigixen que firmem o que xifren.** Hui no firmem les peticions d'autenticació ni rebem assercions xifrades; si ho requerixen, cal generar un parell de claus per al proveïdor de servei i entregar-los el certificat públic.

I dues restriccions nostres, posades a propòsit, que convé advertir-los abans de la primera prova, perquè descobrir-les allí costa una setmana d'anada i tornada:

- **Verifiquem la firma tant del missatge com de l'asserció.** Amb transport HTTP-POST l'asserció viatja dins de la resposta: firmar només el missatge deixa sense verificar la peça que porta la identitat, i al contrari deixa el sobre sense verificar. Diversos IdP firmen només l'asserció per omissió. Si el seu no pot firmar les dues, relaxar-ho és una **decisió de seguretat** i s'ha de parlar.  
- **No acceptem inici de sessió iniciat des de l'IdP.** El flux ha d'arrancar al nostre `/auth/saml/login`. És la protecció que impedix reutilitzar una asserció capturada. Si volen un enllaç des de la intranet, que apunte ahí; si necessiten de veritat un inici des de l'IdP, és un canvi al nostre costat i cal valorar-lo.

## Mentre no hi haja SSO no hi ha comptes de persona

Això no es va decidir: es va descobrir en obrir el pilot. La taula de persones (`hub_users`) **no té columna de contrasenya**. Els seus camps són l'identificador extern, l'entitat de l'IdP i l'origen: eixes identitats només poden vindre de l'IdP. Login local només en tenen els dos rols de gestió, superadministrador i administrador.

I **donar rol d'administrador als provadors no ho resol**, que va ser la primera idea. L'identificador del partner és la clau primària del compte d'administrador, i les organitzacions s'enllacen per eixe mateix identificador: només la fila que el té exactament igual veu els assistents de la Universitat. Quatre provadors serien quatre files de les quals tres obririen el panell amb la llista buida. Es degrada a **una credencial compartida**: sense atribució per persona —que és justament el que necessita la pantalla de revisió que demana Gerència—, amb poders de panell complets i sense poder retirar l'accés a un de sol.

**Deute obert del pilot, amb data de caducitat.** Sis comptes de producció estan **elevats a superadministrador a propòsit**, perquè era l'única manera que els provadors entraren el mateix dia. Dos es van demanar així; els altres quatre es van demanar com a administradors i no ho podien ser pel motiu de dalt.

Mentre dure, sis persones poden canviar proveïdors de model, esborrar assistents i fixar contrasenyes d'administradors. A més **comparteixen contrasenya** —així que l'atribució de les valoracions val el que valga eixe secret— i **no existix canvi de contrasenya per l'usuari mateix** en cap dels dos rols de gestió, així que ni la poden canviar ells ni hi ha pantalla per a fer-ho.

Es desfà creant eixes persones com a comptes de persona amb el seu rol real i la seua organització, i retirant els superadministradors. Eixe paquet de treball ja està planificat.

## El pla per als comptes de persona, en set passos

El paquet és petit perquè **l'alta manual de persones ja existix**: els endpoints i la pantalla de persones estan fets, i l'autorització d'accés a un xatbot ja obri els d'accés autenticat a qualsevol actor de la seua organització. Afig una columna, dos endpoints i una acció de panell.

| Pas | Entregable | Notes de disseny |
| :---- | :---- | :---- |
| 1 | Columna de contrasenya a `hub_users` i via per a fixar-la | Nul significa **login local deshabilitat**, mai «passa sense comprovar». Un administrador pot fixar-la per a una persona *de la seua organització*: obligar que passe pel superadministrador convertix cada alta en un coll d'ampolla. |
| 2 | El login de la persona | Amb les tres defenses dels dos logins que ja hi ha, copiades a consciència: límit d'intents primer, comparació sempre contra un hash esquer perquè el temps de resposta no delate quins correus existixen, i **el mateix error en els tres casos** (compte inexistent, sense contrasenya, contrasenya incorrecta). |
| 3 | El panell: entrar i donar contrasenya | Tercer intent a la pantalla d'inici de sessió i acció nova a la pantalla de persones. Qui pot fer-ho el decidix el servidor, no el client. |
| 4 | Verificació al navegador del recorregut i **dels límits** | Que un provador entre i conversa, i sobretot que *no* veja la secció de plataforma, no òbriga un xatbot d'una altra organització, no fixe contrasenyes i deixe d'entrar en desactivar-lo. |
| 5 | Unicitat del correu del compte d'administrador | Defecte latent trobat investigant això: el correu no té restricció d'unicitat mentre el login pren «el primer» resultat, així que dues files donarien un rebuig intermitent impossible de diagnosticar des de fora. La taula està buida en producció, i per això arreglar-ho és barat hui. |
| 6 | Alta d'administradors, i **diverses persones per organització** | Hui no hi ha *cap* endpoint que cree un compte d'administrador. I la decisió de fons: es recomana que la persona amb rol d'administrador siga la identitat d'administració real i que el compte de partner es quede amb el que és seu —el partner i la facturació—, en compte d'una taula pont que consolidaria quatre taules d'identitat. |
| 7 | Canviar la contrasenya pròpia | No existix en cap rol. És la causa directa que les sis comptes del pilot compartisquen una que els seus propietaris no poden canviar. |

**Seqüència:** independent del desplegament i de la resta de propostes. Porta un interruptor per a apagar el login local quan arribe el SSO: sense ell, «fins que hi haja SSO» es convertix en «per sempre», que és com envellixen els apanys. Contrasenya i SSO són ortogonals: una persona pot tindre les dues vies.

---

### Qüestió 6 · del pilot — el catàleg de procediments

## Normativa i procediment: un sol assistent, no un enrutador

Els assistents del pilot funcionen bé sobre la normativa, però no contesten el que la normativa no diu: quin servei tramita, per on es presenta la sol·licitud, quin termini màxim hi ha, què significa el silenci. Eixa informació és al **catàleg de procediments** (363 fitxes estructurades: servei, col·lectiu, documentació, terminis, silenci, normativa aplicable, enllaç de tramitació), que ara mateix està en revisió: s'ha generat una proposta de posada al dia fitxa a fitxa i els serveis han de completar-la i validar-la.

La qüestió de disseny era si convenia **un segon assistent de procediments amb un enrutador davant**, o **integrar les fitxes al mateix assistent de normativa**. La recomanació és clarament la segona, per tres raons:

- **La gent pregunta les dues coses barrejades, i sovint no les distingix.** Un enrutador obliga a classificar la pregunta *abans* de recuperar — exactament en el punt on el mateix usuari és ambigu. «Puc demanar accés a un expedient, i com ho tramite?» és mitat i mitat: l'enrutador tria un costat i la resposta perd l'altre, en silenci. I la millor resposta a una pregunta mixta necessita **les dues coses al mateix context**: la fitxa (termini d'un mes, silenci negatiu, es presenta al registre electrònic) al costat dels articles de la llei que ho regula. Això només passa si una única recuperació pot tornar-les juntes.
- **L'arquitectura ja tracta l'heterogeneïtat com a metadades, no com a assistents separats.** La recuperació filtra per àmbit i matèries que viuen en taules (dades, no codi); les fitxes entren amb la seua matèria mapejada a eixe vocabulari i amb un **tipus de document** propi (norma / procediment). L'enrutador, en canvi, exigiria construir una peça que hui no existix i duplicar tot el que està calibrat una vegada: llindars, quotes, tema, credencial del giny.
- **La fitxa ja enllaça la seua normativa** (camps de normativa aplicable, que la revisió del catàleg està precisament posant al dia: s'han detectat 28 fitxes citant normes derogades i 154 sense enllaç). En un corpus únic, eixos enllaços es convertixen en cites navegables.

El que la integració **sí que exigix**:

1. **Distingir l'autoritat en la resposta, no en l'enrutament.** Una norma té vigència; una fitxa té *data d'actualització i servei responsable*. La resposta ha de citar distint: «segons la Normativa X (art. N)» front a «segons la fitxa del catàleg (Servei Y, actualitzada el …)». És el mateix mecanisme que ja s'usa per a la vigència no validada: una marca per document que el model ha de verbalitzar.
2. **Recalibrar amb l'instrumental que ja existix.** Afegir 363 documents curts canvia la distribució de la recuperació: es mesura abans i després amb el lot de consultes reals que va servir per a calibrar els llindars del pilot, i s'hi afigen preguntes mixtes noves.
3. **La porta d'entrada és la validació del servei.** Hui 206 de les 362 fitxes analitzades tenen alguna bandera. Un assistent que responga procediment des de fitxes sense validar és pitjor que un que decline: repetiria amb seguretat una norma derogada. **El catàleg actual no s'ingerix tal qual**: entren les fitxes a mesura que els serveis les validen.

## El circuit d'actualització: el formulari edita, el catàleg publica, el corpus sincronitza

La segona pregunta era com muntar l'actualització quan un servei modifica una fitxa. La bona notícia és que este problema **ja està resolt una vegada** per a la normativa, i el catàleg és un cas més fàcil: la font no és un PDF que cal curar, és un registre estructurat que ompli un formulari.

- **La fitxa validada es convertix en document del corpus amb una plantilla determinista.** Els camps del formulari es rendixen mecànicament al format que el corpus exigix (títol i seccions: què és, qui pot, documentació, terminis, silenci, on es tramita, normativa aplicable), amb metadades de servei, matèria, col·lectiu, data d'actualització i qui va validar. Sense IA i sense curació per actualització: la part cara —revisar el contingut— la fa el servei al formulari.
- **L'estat de la fitxa és la porta.** Només publica la fitxa **validada**; un esborrany o una edició pendent de valorar no toca el corpus. L'aprovació humana és la validació del servei; a partir d'ahí, l'automatització manté.
- **La sincronització existent fa la resta.** El mecanisme que manté el corpus normatiu ja compara per empremta (només reingerix el que ha canviat: editar una fitxa costa segons), fa passada en sec, poda el que es retira i porta una **salvaguarda de proporció** perquè una exportació trencada no puga buidar el corpus.
- **Cadència: programada i diària, no per avís immediat — al principi.** Els procediments no canvien per minuts; una passada diària amb un «sincronitzar ara» manual per a la correcció urgent cobrix el cas. L'avís immediat des del formulari acobla les dues aplicacions i no compra quasi res; queda com a evolució si apareix necessitat real. Les primeres passades es fan supervisades i després es programen.
- **Cicle complet**: fitxa retirada del catàleg → poda amb salvaguarda; la versió en castellà es genera després de la validació i s'emparella per identificador de fitxa; i opcionalment **caducitat**: una fitxa sense revalidar en N mesos rep una marca que l'assistent verbalitza — decisió dels serveis, no de codi.

## Com es llig el catàleg: estat complet, no «actualitzats en les últimes hores»

La informació viu a la base de dades del catàleg i es publica a la web. Per a no haver de llegir la web, cal una **consulta de descàrrega del dataset**. Caldria  una **consulta HTTPS autenticada** (token de servei) que torne **l'estat actual complet de les fitxes validades** del catàleg de procediments, en JSON, amb este contracte:
>
> 1. **Només fitxes validades.** Esborranys i edicions pendents de valorar no apareixen: la consulta exposa l'estat *publicat*, no la base de dades.
> 2. **Completitud declarada.** La resposta porta `generated_at` (quan es va generar) i `total` (quantes files conté), i el consumidor comprova que ha rebut `total` files. Una resposta truncada no es pot confondre amb un cens.
> 3. **Per fitxa**: identificador **estable** (el mateix per a sempre, encara que canvie el títol), llengua, tots els camps de la fitxa (títol, servei, contingut, descripció, col·lectiu, documentació, terminis, silenci, normativa aplicable amb enllaços, òrgan de resolució, enllaç de tramitació, matèria) i **data d'última actualització**. Opcional però benvingut: una empremta (hash) del contingut.
> 4. **Les baixes, explícites si pot ser**: una fitxa retirada apareix amb estat `retirada` i la seua data (millor que desaparéixer sense més, perquè distingix «este procediment ja no s'oferix» d'un error de l'exportació). Si no pot ser, l'absència del cens funciona com a baixa i la plataforma porta una salvaguarda que impedix podades massives per error.
> 5. **No cal cap filtre per dates ni per canvis**: la plataforma descarrega l'estat complet i detecta els canvis per empremta. Consum previst: una consulta diària, més alguna puntual manual.

Amb això, el circuit queda: consulta del catàleg → conversió mecànica a documents del corpus → sincronització existent (altes, canvis i baixes per empremta, amb salvaguarda i informe de cada passada). L'única peça nova de veritat és la consulta del costat del catàleg; tota la resta ja està construïda i provada amb el corpus normatiu.

**Seqüència:** el paquet de treball ja està planificat i es pot executar **per tandes**, a mesura que els serveis validen (que a més permet mesurar l'efecte en la recuperació amb volum creixent). Els prerequisits externs són dos: eixa validació i la consulta del dataset; res del paquet no depén del desplegament ni de la resta de propostes.

---

### Per a la reunió

## Decisions a tancar

1. **Autenticació per a agents externs: PAT personal ampliat o token de servei per organització?** **Recomanació (i com està planificat):** reutilitzar el PAT amb els dos permisos nous; l'organització es deriva del propietari del token. Si la reunió exigix un token de servei no personal, és un pas menut més, no un redisseny.  
     
2. **Esquema d'esdeveniment propi o adoptar un estàndard (OpenTelemetry GenAI)?** **Recomanació:** esquema propi mínim amb noms de camp mapejables a les convencions OTel GenAI (el mapatge quedarà documentat amb la guia del registre). L'esdeveniment ací és legal, no d'observabilitat; adoptar l'estàndard sencer arrossega camps que no apliquen.  
     
3. **Confirmar la regla «metadades sí, contingut no» del registre.** Sense el contingut de les converses ni els documents. Si algun cas exigix evidència del contingut, un hash del contingut a l'esdeveniment — mai el contingut.  
     
4. **Posició del registre d'activitat a la planificació.** **Recomanació:** després del desplegament, com a paquet de treball propi. Sense interferir amb el treball en curs.  
     
5. **Sobre els vectors: quina fricció concreta va motivar la proposta?** Val la pena precisar-ho, perquè canvia la resposta. Si és fricció de desenvolupament o de demostracions, es resol amb un `docker compose` sembrat; si és una previsió d'escala o un desplegament sense Postgres, el backend incrustat queda com a opció darrere del protocol del retriever, activable el dia que faça falta i sense cost hui.  
     
6. **Qui pot parametritzar una secció i posar-la en mode automàtic?** Ja no és una decisió de quins apartats existixen — això és configuració que crea qui cura, quan la necessita. El que sí que cal tancar és el **permís**: n'hi ha prou amb el rol de curador per a passar una secció a automàtic, o això l'aprova un administrador? **Recomanació:** crear i provar seccions, el curador; activar el mode automàtic, també el curador, perquè exigix haver fet abans la primera passada manual — i això ja és l'aprovació.  
     
7. **Confirmar les dues salvaguardes de la proposta de seccions dinàmiques.** Les troballes que bloquegen l'auto-ingesta (buida, illegible, necessita JavaScript) i el llindar de la retirada massiva detinguda (**30% per defecte**): si desapareix més d'això en una passada, no es retira res i s'avisa. Les dues són criteris heretables, així que un apartat pot ser més exigent que el seu portal sense tocar codi.  
     
8. **Agents de tercers dins del sistema: s'obri el punt d'extensió, i en quina variant?** La meitat «fora del sistema» ja la cobrix el paquet del registre; el que cal decidir és la de dins. **Recomanació:** explorar primer la variant d'**agents remots orquestrats** (el graf delega la generació en un endpoint extern i conserva dins recuperació, portes de qualitat i registre), perquè no executa codi alié vora dades d'expedients; els **perfils aportats** com a paquet exigixen abans una anàlisi de seguretat i un contracte versionat. Com a paquet de treball propi, posterior al del registre, que ja construïx els seus prerequisits.  
     
9. **Perfils i estratègies de tercers: repositori o plugins de desplegament?** Els pros i contres estan a la taula de la Qüestió 4 (continuació). **Recomanació revisada el 2 de setembre**, arreplegant la insistència de desenvolupament: el **descobriment per *entry points* s'afig ja**, i els perfils i estratègies del propi nucli entren pel mateix mecanisme, perquè això obliga el motor a no dependre de res que no passe pel registre; el que **no** es fa encara és congelar els protocols d'estratègia com a contracte públic, que han canviat dues vegades en un mes per mesura i es declaren explícitament inestables (0.x) fins que hi haja un tercer real. L'alta de codi de motor per la interfície en runtime queda descartada. **Ja és un bloc de treball planificat (PLG, dos passos)**, i en planificar-lo ha canviat un detall: els dos grups d'*entry points* són `govgenai.graph_profiles` i `govgenai.retrieval_pipelines`, no «estratègies»: una estratègia solta no la selecciona la configuració, la compon un perfil; el que sí selecciona la configuració, a més del perfil, és el pipeline de recuperació. Una estratègia nova entra dins d'un perfil. També ha eixit que el frontend duia els noms de perfil i mode fixats al codi, que és justament el que un perfil instal·lat no podria travessar: el bloc ho corregix.

10. **Funcions del catàleg: el canal del nivell 2 de la Instrucció 02/2026, amb dos orígens.** L'observació que gestionar codi dins de la ferramenta és reinventar la roda es resol sense triar: origen **autoservici** (nivell 2: la persona referent registra amb declaració responsable, auditoria i sandbox automàtics, ús immediat i revisió posterior) i origen **empaquetat** (nivell 3: codi al repositori de la UADTI, *entry point* `govgenai.funciones`, semver, corre al procés amb la confiança en qui instal·la). El que centralitza la plataforma en els dos casos és el registre, la revisió posterior, el manifest d'execució, la traçabilitat i el contracte, no el codi. **Tres coses a confirmar a la reunió:** (a) que la UADTI assumisca la cua de revisió posterior i el manteniment de les regles de l'auditor com a caixa d'eines, que és el que la Instrucció li encomana; (b) que UADTI i OIATI donen per bo el règim d'execució al node institucional en compte de l'equip local (regla 2); (c) que el vostre equip escriga la primera funció empaquetada, que és la manera més ràpida de trobar on el contracte està mal.  
     
10. **Caducitat editorial: què passa amb l'esdeveniment que ja ha ocorregut però continua publicat?** No és una decisió de codi sinó del propietari del contingut: retirar-lo del corpus per data, deixar que el xatbot responga en passat, o moure'l a un apartat d'arxiu. La proposta de seccions la documenta amb les opcions; convé portar-la també al responsable del portal.  
      
11. **Quin nom DNS institucional tindrà el servei, i quan?** És el **prerequisit del SSO**, no un detall d'estètica: l'identificador del proveïdor de servei i l'URL de retorn es construïxen sobre ell, i canviar-los obliga a registrar el servei de nou davant l'IdP. **Recomanació:** demanar-lo en el mateix correu que les dades de SAML i no registrar res fins que existisca.  
      
12. **Es relaxa l'exigència de firma si l'IdP de la Universitat només firma l'asserció?** Hui exigim firma del missatge *i* de l'asserció. **Recomanació:** no relaxar-ho sense una alternativa —comprovar primer si l'IdP pot firmar les dues, que molts poden amb un canvi de configuració—, i si no es pot, documentar la decisió i el risc acceptat abans d'encendre el SSO.  
      
13. **Els sis comptes elevats del pilot: quan es baixen, i a quin rol cada u?** Es desfà amb el paquet de comptes de persona, creant eixes persones amb el seu rol real i la seua organització. El que cal decidir és **qui ha de ser revisor i qui administrador**, i si eixe paquet s'avança a la resta. **Recomanació:** avançar-lo, perquè el pilot ja està en marxa i cada dia que passa és un dia amb sis superadministradors i una contrasenya compartida.

14. **Què significa «fitxa validada» del catàleg de procediments, i qui ho decidix.** És la porta de tot el circuit: cap fitxa entra a l'assistent sense passar-la. Cal fixar qui la marca (el servei responsable? amb vistiplau de qui?) i quina revisió mínima comporta — com a mínim, la normativa aplicable posada al dia, que és on la revisió ha trobat més banderes.

15. **Les fitxes entren per tandes per servei, o totes quan acabe la revisió?** **Recomanació:** per tandes, a mesura que cada servei valida. Permet mesurar l'efecte en la recuperació amb volum creixent i dóna valor al pilot des de la primera tanda, en lloc d'esperar el servei més lent.

16. **Caducitat de les fitxes: què passa amb una fitxa que ningú no revalida?** Opcions: marcar-la com a pendent de revisió (l'assistent ho diu en citar-la), retirar-la del corpus, o no fer res. **Recomanació:** marcar-la, amb un termini (per exemple, dotze mesos) i avís al servei responsable — retirar informació correcta per vella és pitjor que servir-la amb l'avís.

---

Fonts: el codi real del repositori — per a la qüestió 4: `server/app/routers/hub_chatbots_router.py` (creació de xatbots), `server/app/modules/agents_hub/agent/public_graphs/` (factoria, registre de perfils, estratègies) i `frontend/src/admin/pages/ChatbotsPage.tsx` (fragment del widget); per a la seua continuació: `server/app/routers/redaccion/scripts_router.py` i `server/app/modules/redaccion/contracts/blocks.py` (el codi incrustat) i `server/app/modules/redaccion/pipelines/` (contractes i factoria d'extracció); per al registre: `server/app/core/auth/pat/scopes.py` i `server/app/modules/redaccion/services/anonymization/`; per a la curació: `server/app/modules/curation/` (`quality_job.py`, `site_crawler.py`, `selection_service.py`); per al SSO: `server/app/core/auth/saml/` i `server/app/routers/saml_auth_router.py`; per als procediments: el projecte de revisió del catàleg (363 fitxes estructurades, informe de desfasament normatiu inclòs) i la sincronització del corpus (`server/app/modules/agents_hub/ingestion/corpus/`) — i la planificació interna del projecte, on cada proposta d'este informe té el seu paquet de treball detallat pas a pas.  
