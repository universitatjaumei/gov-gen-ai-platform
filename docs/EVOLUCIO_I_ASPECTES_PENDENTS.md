### Gov Gen AI Platform · Evolució i aspectes pendents

# Evolució i aspectes pendents

*Reunions amb la Unitat d’Anàlisi i desenvolupament · actualitzat l'1 set 2026 · preparat sobre el codi real del repositori*

Desenvolupament va portar tres propostes: fer servir bases vectorials incrustades en xatbots de corpus estable, obrir la plataforma perquè agents externs registren la seua activitat i utilitzen funcionailtats com l'anonimització, i que les seccions web d'actualització permanent (jornades, esdeveniments) alimenten el seu xatbot sense curació manual. Les tres apunten a preocupacions reals, i dues es convertixen directament en blocs de treball. La primera s'ajorna —no per la idea, sinó perquè Postgres està al sistema per moltes més coses que els vectors— i queda com a opció oberta sense cost. La segona és estratègica i encaixa: la meitat de les peces ja estan construïdes. I en la tercera hi ha una: la ingesta automàtica ja existix i corre al scheduler, encara que no es veja des de la interfície; el que falta és tancar-ne el cicle de vida i que els apartats siguen paràmetres que configura qui cura, no res fixat al codi. Els dos paquets de treball ja estan planificats pas a pas.   
S’ha plantejat també una una quarta qüestió, sobre l'arquitectura dels xatbots: si crear-ne un genera codi dins del runtime del producte. No ho fa —és una fila de configuració que interpreta un motor únic—, i de l'alternativa que proposava el correu (una extensió de LangGraph a nivell d'API) ix una proposta que mereix reunió pròpia: que tercers implementen agents dins i fora del sistema via API. I s'hi afig ara una cinquena qüestió, relacionada amb el pilot que ja està en marxa: el SSO institucional, i què passa amb els comptes de persona mentre no hi siga.

- **1 · Bases vectorials incrustades** — *Ajornat, amb la porta oberta.* Postgres continuaria sent necessari per a tot la resta, i la recuperació híbrida porta llindars calibrats que caldria refer. A més el corpus encara es mou. L'opció queda disponible sense pagar res hui: el retriever ja s'injecta darrere d'un protocol.  
- **2 · Registre d'activitat i serveis cap a fora** — *Recomanat.* La preocupació per l'escalabilitat té bona part de resposta ja al codi: el monolit està partit per dins. I la proposta encaixa amb l'arquitectura i amb l'AI Act. Ja està planificada com a paquet de treball propi, per a després del desplegament.  
- **3 · Seccions dinàmiques sense curació manual** — *Ja en marxa; falta tancar el cicle.* L'auto-ingesta de pàgines noves i la reingesta de les canviades ja existixen, amb tests i al scheduler. Falta que l'apartat siga un paràmetre de curació —hui és un lloc sencer— i tancar el cicle: retirada, porta de qualitat i diari. El paquet de treball ja està planificat, en set passos.  
- **4 · ¿Generador de codi o framework?** — *Actualment* crear un xatbot és un `INSERT` de configuració i un motor únic la interpreta en temps de petició. L'«extensió de LangGraph» que proposa el correu és com està construït l'interior; obrir-la a tercers —dins i fora del sistema, via API— es recull com a proposta per a la reunió.  
- **4·bis · Scripts copiats** — Actualment en el mòdul informes es poden generar scripts. El codi d'un script aprovat s'incrusta copiat al bloc de cada plantilla: un bug s'arregla N vegades. Com a consequència del suggeriment es planifica un catàleg de funcions versionades i compartibles — hui per als informes, en el futur per actes activitats o  fases d'expedient. A més, per a futures evolucions es valora la possiblitat d’evolucionar els perfils i les estratègies de l’actual fórmula a través del repositori a un model de plugins. .  
- **5 · SSO institucional i comptes de persona** — *Depén d'un requisit extern.* El SAML està implementat i apagat per configuració. El que el bloqueja no és codi: són les metadades de l'IdP i un nom DNS institucional. Mentrestant no hi ha comptes de persona amb contrasenya —el paquet de treball per a tindre'n ja està planificat— i el pilot funciona amb sis comptes elevats que caldrà baixar.

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
     
9. **Perfils i estratègies de tercers: repositori o plugins de desplegament?** Els pros i contres estan a la taula de la Qüestió 4 (continuació). **Recomanació:** repositori mentre els perfils els escriga l'equip; el mecanisme d'*entry points* s'afig el dia que hi haja el primer tercer real amb un perfil que mantindre — és additiu i no cal decidir-ho hui. L'alta de codi de motor per la interfície en runtime queda descartada. El que és per API des del principi són les **funcions del catàleg**, que sí que van amb sandbox.  
     
10. **Caducitat editorial: què passa amb l'esdeveniment que ja ha ocorregut però continua publicat?** No és una decisió de codi sinó del propietari del contingut: retirar-lo del corpus per data, deixar que el xatbot responga en passat, o moure'l a un apartat d'arxiu. La proposta de seccions la documenta amb les opcions; convé portar-la també al responsable del portal.  
      
11. **Quin nom DNS institucional tindrà el servei, i quan?** És el **prerequisit del SSO**, no un detall d'estètica: l'identificador del proveïdor de servei i l'URL de retorn es construïxen sobre ell, i canviar-los obliga a registrar el servei de nou davant l'IdP. **Recomanació:** demanar-lo en el mateix correu que les dades de SAML i no registrar res fins que existisca.  
      
12. **Es relaxa l'exigència de firma si l'IdP de la Universitat només firma l'asserció?** Hui exigim firma del missatge *i* de l'asserció. **Recomanació:** no relaxar-ho sense una alternativa —comprovar primer si l'IdP pot firmar les dues, que molts poden amb un canvi de configuració—, i si no es pot, documentar la decisió i el risc acceptat abans d'encendre el SSO.  
      
13. **Els sis comptes elevats del pilot: quan es baixen, i a quin rol cada u?** Es desfà amb el paquet de comptes de persona, creant eixes persones amb el seu rol real i la seua organització. El que cal decidir és **qui ha de ser revisor i qui administrador**, i si eixe paquet s'avança a la resta. **Recomanació:** avançar-lo, perquè el pilot ja està en marxa i cada dia que passa és un dia amb sis superadministradors i una contrasenya compartida.

---

Fonts: el codi real del repositori — per a la qüestió 4: `server/app/routers/hub_chatbots_router.py` (creació de xatbots), `server/app/modules/agents_hub/agent/public_graphs/` (factoria, registre de perfils, estratègies) i `frontend/src/admin/pages/ChatbotsPage.tsx` (fragment del widget); per a la seua continuació: `server/app/routers/redaccion/scripts_router.py` i `server/app/modules/redaccion/contracts/blocks.py` (el codi incrustat) i `server/app/modules/redaccion/pipelines/` (contractes i factoria d'extracció); per al registre: `server/app/core/auth/pat/scopes.py` i `server/app/modules/redaccion/services/anonymization/`; per a la curació: `server/app/modules/curation/` (`quality_job.py`, `site_crawler.py`, `selection_service.py`); per al SSO: `server/app/core/auth/saml/` i `server/app/routers/saml_auth_router.py` — i la planificació interna del projecte, on cada proposta d'este informe té el seu paquet de treball detallat pas a pas.  
