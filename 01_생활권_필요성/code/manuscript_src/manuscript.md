# Grids fill people, not places: Testing the necessity of living zones for walkable public services in Seoul

## Abstract

Cities increasingly plan daily life through living zones, such as neighbourhood units, life circles and 15-minute neighbourhoods, that differ from their administrative districts. Yet walking accessibility can be measured, and facilities located, on fine grids, so why are living zones needed? We test this in Seoul, whose 2030 Living Zone Plan diagnoses and plans daily public services for its 116 living zones. Using 100 m population grids, street-network walking times and facility records for 2020 and 2025, we measure whether residents can walk to all six planned service domains within 10 minutes. We then place the same facility additions under grid-based rules and minimum standards set by gu (district), living zone or dong (sub-district). Only 3.7–5.3% of residents reach all six domains, and in 38–50 living zones no resident does. Grid-based placement fills people but not places. Exact maximisation raises completion to 24%, yet every grid rule leaves 13–21 living zones, home to about a million residents, where no resident completes the bundle. A minimum standard at the living-zone scale can fill every living zone with the same facilities, as integer programming proves, at a cost of at least 1.3 percentage points of completion under a 5% minimum. The same standard set by gu changes almost nothing, and set by dong it could not be met. Official boundaries also cut walkable access less than random partitions of equal number (p ≤ 0.04, four facility types). In Seoul, a minimum set at the living-zone scale was needed to fill every place.

**Keywords:** Living zone; 15-minute city; Walking accessibility; Minimum service standard; Facility location; Planning unit; Seoul

## 1. Introduction

Planning walkable, self-contained neighbourhoods has returned to the centre of urban policy. The most visible expression is the 15-minute city, which asks that the services residents need every day lie within a short walk or cycle of home (Moreno et al., 2021; Allam et al., 2022). Paris has made it a municipal programme (Ville de Paris, n.d.), Melbourne plans by 20-minute neighbourhoods (Chau et al., 2022), and Shanghai, Melbourne and Portland have each written x-minute neighbourhoods into their plans (Rao et al., 2024). In China, Shanghai's 2016 planning guidance introduced the 15-minute community life circle, a walkable area equipped with basic daily services and public space (H. Wu et al., 2021), and the national standard for residential areas now organises planning by 15-, 10- and 5-minute life circles (Ministry of Housing and Urban-Rural Development, 2018). Korea's Life SOC (social overhead capital) programme promises gyms, libraries and childcare "within ten minutes" of home (Office for Government Policy Coordination, 2019). A growing literature measures how far real cities fall short of these goals (Logan et al., 2022; Papadopoulos et al., 2023; Willberg et al., 2023).

What these programmes share is a planning unit. They plan daily services by living zones: territories smaller than a city and larger than a block, which are often not the city's administrative districts. The idea goes back to Perry's (1929) neighbourhood unit, which sized a residential area by the walking catchment of an elementary school and equipped it with shops, parks and community facilities (Lawhon, 2009; Y. Park & Rogers, 2015). Researchers now go further and delineate living zones from data rather than from administrative maps, using mobile-phone, satellite-positioning and travel-survey flows (Ratti et al., 2010; Ha & Lee, 2016; Jiao & Xiao, 2022; Y. Wu & Zhang, 2026). Seoul's 2030 Living Zone Plan is a leading example. It divides the city into 116 local living zones that group neighbouring administrative units, and for each of them it identifies which daily public services should be supplied first (Seoul Metropolitan Government, 2018, 2019).

Yet the tools that made these ideas measurable also make the living zone look dispensable. Walking accessibility can now be computed cell by cell on fine grids, which avoids the aggregation errors of zone-based measures (Hewko et al., 2002; Stępniak & Jacobs-Crisioni, 2017). Facilities can be located on the same grid by optimisation models that maximise coverage or favour the worst-off (Church & ReVelle, 1974; Marsh & Schilling, 1994), and recent work places amenities for the 15-minute city on hexagonal grids or census blocks without any planning zones (Bruno et al., 2024; Horton, Logan, et al., 2025). Fixed, non-overlapping neighbourhood boundaries have also been criticised as a poor description of where people live (Hipp & Boessen, 2013), and planning theory warns against assuming that the local scale is always preferable (Purcell, 2006). If the grid can both diagnose and fix, why plan through living zones? Previous studies have asked whether living-zone boundaries match the communities residents form through their daily trips (Ha et al., 2024; J. Park et al., 2026), and how boundaries change the supply of local facilities planned for a zone (J. Park et al., 2023). They have not asked whether the living zone itself is needed.

This paper tests that necessity empirically. Our argument is that the answer depends on the goal. If the goal is only that more people reach services, the grid may suffice. Living-zone plans, however, diagnose and supply services zone by zone, and so imply a goal about places as well as people: no living zone should be left without the services the plan lists. We regard living zones as necessary for that goal when three conditions hold. Planning on the grid fails to fill every zone. A minimum standard set at the living-zone scale succeeds. And neither the larger district nor the smaller administrative unit can do the same job.

We test these conditions in Seoul, one of the few cities whose population grid, facility registers, street network, mobility flows and official living-zone boundaries are all publicly available. Using a 100 m population grid, walking times on the street network and facility records for 2020 and 2025, we measure whether residents can walk to all six public-service domains of Seoul's plan within 10 minutes. We then place the facilities that Seoul actually added between 2020 and 2025 under grid-based and zone-based rules. Three research questions (RQs) structure the analysis:

- **RQ1**: How completely do Seoul's living zones provide the bundle of daily public services that the living-zone plan lists, compared with everyday commercial functions?
- **RQ2**: Can grid-based facility placement, whether it maximises total access or favours access-poor residents, fill every living zone?
- **RQ3**: At which planning unit (gu, living zone or dong) can a zone-level minimum standard be met with the facilities actually added, and do the official living-zone boundaries matter?

Section 2 reviews the literature and states the gaps, Section 3 describes the data and placement rules, Section 4 answers the three questions, and Section 5 discusses why grids leave places empty, why the living-zone scale works and what this means for planning.

## 2. Literature review

### 2.1. Defining and contextualising living zones

The living zone descends from the neighbourhood unit. Perry (1929) bounded a residential neighbourhood by the walking catchment of an elementary school, placed shops at its edge and community facilities at its centre, and made the unit the basis for counting and supplying daily services. Later movements, from the garden city to new urbanism and eco-urbanism, revised the area, population and boundary of such units but kept the idea that daily life should be planned within them (Sharifi, 2016; Y. Park & Rogers, 2015). The concept has been criticised as physical determinism, although historians argue that it was a design model for arranging facilities and opportunities for contact rather than a tool of social engineering (Lawhon, 2009). The 15-minute city inherits both the idea and the critique (Khavarian-Garmsir et al., 2023; Marchigiani & Bonfantini, 2022). Critics add that it can neglect who benefits, for example where improved local access accompanies gentrification (Elldér, 2024), that the strong decentralisation it proposes is unrealistic, and that it counts destinations rather than asking whether they suffice (Mouratidis, 2024).

East Asian planning has turned the neighbourhood unit into an explicit hierarchy of living zones. In Chinese cities, the life circle was first proposed to restructure daily activity spaces that had become scattered after the end of the work-unit system (Liu & Chai, 2015). It then became a planning paradigm, with Shanghai's 2016 guidance and a national standard of 15-, 10- and 5-minute life circles (Ministry of Housing and Urban-Rural Development, 2018; Yang & Qian, 2024; Qi et al., 2025). Empirical studies find that service provision in these life circles is uneven, with high convenience in central districts and shortfalls in the suburbs (Weng et al., 2019; H. Wu et al., 2021; Ma et al., 2023). In Korea, the Life SOC programme set minimum provision standards for daily facilities, such as an elementary school within a 15-minute walk (Shin et al., 2024). Korea's existing living infrastructure has been found to be evenly distributed between metropolitan and provincial cities, but planning has paid little attention to the distance between facilities and homes (Kim et al., 2020). Seoul's 2030 Living Zone Plan formalised the hierarchy at two levels, five regional and 116 local living zones, and made the local living zone the unit in which daily public services are diagnosed and their priority supply is set (Seoul Metropolitan Government, 2018, 2019).

A second strand of research asks where living zones should be drawn. Interaction data have been used to redraw regions from telephone networks (Ratti et al., 2010), to identify neighbourhoods from social-media check-ins (Cranshaw et al., 2012) and to delineate life circles from mobile-phone and point-of-interest data (Jiao & Xiao, 2022; Y. Wu & Zhang, 2026). In Seoul, community detection on travel flows has been used to derive functional living zones and to benchmark the official ones (Ha & Lee, 2016; Ha et al., 2024; J. Park et al., 2026). These studies find that data-derived zones often overlap with administrative ones but are irregular in shape, and that neighbouring zones share facilities (Ratti et al., 2010; Jiao & Xiao, 2022). They take the need for living zones as given and ask how to draw them.

Why should services be planned by territory rather than by person? Three related ideas give reasons. Spatial equality asks that provision be equal across areas, territorial justice asks that provision among areas reflect their needs, and minimum standards ask that no area fall below a basic level; these are distinct concepts with different measures (Hay, 1995). Territorial justice has a long empirical tradition of testing whether provision among local authorities and neighbourhoods matches need, and it often finds that it does not (Davies, 1968; Boyne & Powell, 1991; Hastings, 2007). Theories of multi-level governance add that task-specific jurisdictions can sit alongside general-purpose ones (Hooghe & Marks, 2003), and the debate on place-based policy asks when interventions should target places rather than people (Barca et al., 2012; Kline & Moretti, 2014). These literatures test whether areas are served fairly. They do not test at which scale a minimum standard has to be set for every area to be served, which is the question of this paper.

Choosing a unit also shapes what can be seen. The modifiable areal unit problem means that the same pattern produces different results at different scales and zonings (Openshaw, 1984; Fotheringham & Wong, 1991). The uncertain geographic context problem warns that residents' actual exposure rarely matches administrative boundaries (Kwan, 2012). For accessibility, boundaries cut off services that residents can reach across them (Tao et al., 2018; Gao et al., 2017), and in Seoul the facility supply judged adequate for a living zone changes with how the zone is drawn (J. Park et al., 2023). Measures of spatial equity can also reach opposite conclusions depending on whether they count facilities within zones or distances from homes (Talen & Anselin, 1998). These problems are usually treated as sources of error. Here they become the object of study, because a unit that hides deficits cannot be used to monitor their removal.

### 2.2. Walkable service bundles and grid-based location planning

Research on the 15-minute city has turned the neighbourhood ideal into measurable indicators. Reviews list dozens of measures that differ in the services they include, the travel thresholds they use and the way they combine services (Papadopoulos et al., 2023). Logan et al. (2022) defined the x-minute city as the time within which a resident can reach the nearest of every essential amenity, a definition that treats services as a bundle that is complete only when every element is present. Most measures are now computed at fine resolution, on hexagonal grids (Olivari et al., 2023) or cadastral parcels (Ferrer-Ortiz et al., 2022), and are reported as citywide shares, maps or inequality indices. They show that dense European cities already reach many services well within 15 minutes (Staricco, 2022), that within-city inequality remains large (Vale & Lopes, 2023) and that disadvantaged communities have lower access (Nicoletti et al., 2023). Some studies identify which neighbourhoods meet a 20-minute standard (Calafiore et al., 2022). Proximity also matters for behaviour: differences in nearby amenities explain most of the variation in how much residents shop and visit locally (Abbiasov et al., 2024). The sufficiency perspective in transport justice gives the normative basis for such bundles. Every person should reach at least a minimum of each essential service (Lucas et al., 2016; Martens, 2016; Pereira et al., 2017), and sufficiency thresholds can be operationalised for whole cities (van der Veen et al., 2020), although most studies still set them without empirical justification (Jasso Chávez et al., 2026).

Facility location models provide the tools to close the gaps that such indicators reveal. The maximal covering location problem places a fixed number of facilities to maximise the population within a service distance (Church & ReVelle, 1974; Murray, 2016). A large literature adds equity objectives that favour the worst-off and measures the efficiency they cost (Marsh & Schilling, 1994; Karsu & Morton, 2015; Bertsimas et al., 2011), and hierarchical location models place services at several levels of a spatial hierarchy (Şahin & Süral, 2007). Aggregating demand to zones introduces measurement and coverage errors that fine grids avoid (Hillsman & Rhoda, 1978; Current & Schilling, 1990; Francis et al., 2009), which is one reason grid- and point-based models have become the norm.

Applied to the 15-minute city, these tools optimise over people. Bruno et al. (2024) redistributed services on 200 m hexagonal cells to equalise access per person across cities worldwide. Horton, Logan, et al. (2025) located grocery outlets in 500 US cities by minimising an inequality-adjusted mean distance over census blocks, with a scalable formulation for such equitable location problems (Horton, Murrell, et al., 2025). Xu et al. (2020) showed that relocating facilities could halve travel costs, and Chen et al. (2023) used a maximal covering model to raise the population within 15 minutes of primary care in Shenzhen. Huang and Khalil (2023) formulated walkability optimisation across several amenity types as an integer programme and applied it to low-walkability neighbourhoods in Toronto. Even models built for Chinese life circles impose their coverage targets on the study area as a whole (Zhai et al., 2023). An operations-research agenda for the 15-minute city notes that most of the literature has stayed with defining and measuring access (Arslan & Laporte, 2025).

Whether these solutions leave whole places unserved is rarely part of the objective. Location research has long recognised that maximising coverage favours dense areas and can leave sparse ones behind, as in emergency services for rural areas (Chanta et al., 2014). It has responded by adding equity as a second objective or as a side constraint, including allocations across service units (Mandell, 1991; Batta et al., 2014). Where zones enter 15-minute city optimisation, they enter as targets fixed from the outset. Jafari et al. (2023) set coverage targets for each destination type across several neighbourhoods of a hypothetical new town. Pemberton et al. (2026) modelled the placement of additional destinations in Melbourne until at least 80% of residents in each activity-centre catchment could reach every destination type within 10 minutes. Access improved, but in low-density suburbs the new destinations were likely to be underused. These studies assume that a zone-level target is wanted and fix its unit in advance. They do not ask whether the same facilities placed on the grid would already fill the zones, or at which unit the target should be set.

### 2.3. Research gaps in assessing the necessity of living zones and this study's contributions

Three gaps limit the use of these literatures for deciding whether living zones are needed. First, 15-minute city studies mostly measure everyday amenities and report citywide shares, maps or inequality indices, and those that judge neighbourhoods against a standard do so for amenities rather than for the public services that living-zone plans list (Calafiore et al., 2022). Second, location studies for the 15-minute city optimise population coverage or distributional equity on fine grids or blocks. Zone constraints are standard tools in operations research (Mandell, 1991; Batta et al., 2014; Şahin & Süral, 2007), but where zones appear in 15-minute city planning they are imposed as targets rather than tested against grid rules. In our searches of the 15-minute city, facility location and living-zone literatures we found no study that places the same facilities under grid- and zone-based rules and counts the planning zones left without complete access to every service domain. Third, studies of Seoul's living zones have asked how they should be delineated from mobility data (Ha et al., 2024; J. Park et al., 2026) and how alternative boundaries change the facility supply judged adequate (J. Park et al., 2023). They have not compared, under the same facility additions, at which planning unit a zone-level minimum standard can actually be met.

This study addresses these gaps in three ways. (1) It measures bundle completion for the six public-service domains of Seoul's living-zone plan and diagnoses it zone by zone. (2) It places the same facility additions under grid-based rules, solved exactly where possible, and under zone-based minimum standards, and shows that grid rules fill people but leave living zones empty. (3) It sets the same minimum standard by gu, living zone and dong, compares random partitions with the same number of zones, and tests whether official living-zone boundaries cut walkable access less than such partitions. The novelty lies not in the zone constraint itself but in using it to test at which scale a place-based minimum can work.


## 3. Data and methods

### 3.1. Study area: Seoul

Seoul covers 605 km² and had 9.34 million residents in 2024 (9.64 million in 2019), living on 30,785 populated 100 m grid cells. Its planning hierarchy is fully nested (Table 1, Fig. 1). The 25 gu are autonomous districts with their own elected councils and budgets (mean population 373,515). The 424 administrative dong are the smallest units of local administration (mean 22,023). Between them, the 2030 Seoul Living Zone Plan, adopted in March 2018, defines five regional living zones and 116 local living zones (Seoul Metropolitan Government, 2018). Each local living zone was drawn by grouping three to five dong with about 100,000 residents, taking into account topography, local centres and travel linkages between dong, without crossing gu boundaries; residents' panels of 30–40 members took part in planning each zone (Seoul Metropolitan Government, 2019). Today their populations average 80,499 (range 21,165–148,376). Each local living zone contains 3.7 dong on average (range 1–7), and each gu contains 4.6 local living zones (range 3–7). We refer to local living zones simply as living zones.

The plan is explicit about what a living zone is for. It lists eleven domains of daily public services, of which seven are diagnosed at the local living-zone level: parks, parking, libraries, senior leisure, youth and children's facilities, childcare and public sports. Supply in each domain was diagnosed zone by zone against a 10-minute walking distance (Seoul Metropolitan Government, 2019, p. 86), and the plan identifies priority facilities for living zones where residents request them, where none lies within a 10-minute walk (an 800 m radius) and where provision falls below the Seoul average (Seoul Metropolitan Government, 2018). These priorities guide later facility programmes rather than bind them. The plan thus treats the living zone as the unit in which shortfalls are found and addressed, and the goal we test, that no living zone be left without the services it lists, follows from that design.

Seoul is also well suited to such a test because the data it needs are public. Residential population on a 100 m grid, facility registers with addresses for every public service type, an open street network, mobile-phone-based origin–destination flows between dong and the official living-zone boundaries are all available for the same years. Several countries publish fine population grids, but few cities publish them together with official living-zone boundaries and mobility flows. We therefore use Seoul as a test case and leave replication in other cities to future work.

### 3.2. Data sources

**Population.** Residential population on the national 100 m grid for 2019 and 2024 from Statistics Korea's Statistical Geographic Information Service, used for the 2020 and 2025 analyses respectively.

**Walking travel times.** Cell-to-cell walking times on the OpenStreetMap pedestrian network, using the January 2020 and January 2025 snapshots for Seoul and a 2 km buffer, at 4.0 km/h. Times are stored for all origin–destination pairs up to 30 minutes (22.1 and 22.6 million pairs). A 10-minute network walk at this speed covers about 670 m, which is stricter than the plan's 800 m radius; Section 4.4 reports 12- and 15-minute thresholds.

**Facilities.** An inventory of 32 facility types for 31 December 2019 and 31 December 2024 (584,766 records; source dates for kindergartens, community service centres and cultural facilities differ by up to six months), built from public licensing records (LOCALDATA, Ministry of the Interior and Safety), annual official registers and the Seoul Open Data Plaza. Records without source coordinates were geocoded only when the road address and building number, or the parcel number, matched exactly. Each record was assigned to its 100 m grid cell. Three research layers needed for the plan's service domains were added; they are prepared for release with the facility inventory but not yet part of it. Public sports facilities come from the Ministry of Culture, Sports and Tourism's national inventory (387 and 456 facilities); their coordinates are of moderate accuracy, and Section 4.4 repeats the main counts with the facilities whose coordinates were verified. Community child centres come from the Seoul Open Data Plaza (307 centres). Only a current list without opening dates exists, so it is used for both years, which may overstate access in 2020. Parks come from the park layer of the 2030 Seoul Living Zone Plan (1,886 parks; 2018, held fixed). Because parks are areas, every grid cell that overlaps a park polygon is treated as a park destination.

**Service bundles.** We compare three bundles (Table 2). (a) Everyday functions: the seven categories of the accessibility inventory (education, culture, childcare and welfare, personal services, retail, health, and administration and safety). (b) The four amenities of Logan et al. (2022): pharmacy, supermarket (large stores and small food retailers), park and elementary school. (c) Planned public services: six of the seven local service domains of Seoul's plan, namely park, public library, senior leisure, youth and children, childcare and public sports. Parking is excluded because it serves cars rather than walking residents. Youth and children combines youth centres and community child centres, and childcare counts all childcare centres, public and private. The six-domain bundle and its 10-minute threshold follow the plan's domains and its 10-minute walking criterion, but they are our operationalisation, not an official indicator.

**Boundaries.** Administrative dong (424; boundaries of July 2023), official living zones (116), gu (25) and, for comparison, 116 mobility communities derived from daytime non-commuting origin–destination flows between dong in the Seoul Living Mobility Dataset with the Leiden algorithm (J. Park et al., 2026), derived for each year from its January flows. They represent zones drawn from where residents actually go.

### 3.3. Placement rules: grid-based versus zone-based

All experiments ask one question: given a fixed set of facility additions, where should they go, and does the answer fill every living zone? The additions for each facility type are its net increase in facility-occupied grid cells between 2020 and 2025. For the bundle they are public library 31, senior facility 93, youth centre 11, public childcare centre 200 and public sports facility 46, or 381 in total; parks are not placed. For single facilities we also use cultural facilities (32), public kindergartens (54) and community centres (8). The net increase is smaller than the number of facilities that opened, because some closed, and it is not a monetary budget. On the 2020 stock, placing these additions re-plays the five years that followed. On the 2025 stock, which already contains the actual additions, it is a forward-looking scenario of a further round of the same size. Candidate sites are populated or business-occupied cells without an existing facility of the same type. Every rule places exactly the same additions; only the rule changes.

**Grid-based rules** treat the city as a surface of people and place facilities to optimise outcomes over people.

- *Grid efficiency* places each facility where it newly reaches the most residents.
- *Grid access-poor weighting* gives extra weight to residents in cells where few of the nearby residents were reached before placement.
- For the bundle, *grid bundle maximisation* applies the maximal covering location problem (Church & ReVelle, 1974) to the whole bundle. It chooses all 381 sites at once to maximise the number of residents who complete the bundle, and we solve it exactly as an integer programme (Appendix A, Eq. A.1).
- *Facility-by-facility* planning, which mirrors how separate departments plan their own facilities, solves an exact covering problem for each type on its own.
- A *coordinated* rule rewards each cell by a convex function of the number of domains it reaches (Appendix A). It favours cells close to completion less sharply than bundle maximisation and, among the grid rules, reaches the bottom 20% of residents best.

For single facilities, the grid and zone rules are solved greedily; for the bundle, bundle maximisation, facility-by-facility planning and the zone minimum standards are integer programmes, and the coordinated rule is greedy. Single-facility thresholds follow the walking times used for each facility type: 15 minutes for libraries, cultural facilities, senior facilities, youth centres and community centres, 10 minutes for public kindergartens and 5 minutes for public childcare centres. The bundle uses 10 minutes for all domains.

**Zone-based rules** treat the city as a set of places. They first meet a minimum standard in every unit of a chosen planning unit and then use the remaining facilities for efficiency. We apply the same rule to gu, official living zones and dong, so that only the planning unit changes. For single facilities, the minimum is a coverage share τ equal to 0.6 times the population-weighted median dong coverage of that facility, following the convention of setting deprivation lines at 60% of the median (Sun & Thakuriah, 2021). A hybrid rule meets the living-zone minimum first and places the rest with access-poor weights. For the bundle, the minimum is that at least τ = 1% or 5% of a unit's residents complete the bundle. We add this to the bundle maximisation as a constraint whose shortfall carries a heavy penalty, so that meeting the minimum takes priority over total completion (Appendix A, Eq. A.2). Where fewer than τ of a unit's residents live in cells that could complete the bundle at all, the minimum is lowered to that share; in practice this cap never bound. The two levels are deliberately low. A 1% minimum asks only that some residents of every zone can walk to all six domains, and 5% roughly matches the citywide completion rate before placement.

### 3.4. Indices for evaluation and analytical procedure

#### 3.4.1. Evaluation indices

Every rule is scored on three report cards: total access, access for the access-poor, and places. A rule that serves people well can still fail places, and the question is whether only zone-based rules pass the third card.

- **Total access**: the share of residents who reach a facility within its threshold (single facilities) or complete the bundle (bundle completion rate). Completion follows the x-minute definition of Logan et al. (2022): a resident completes the bundle when the slowest of the nearest facilities of every domain is within the threshold.
- **Access-poor residents**: for single facilities, the share reached among residents in the cells with the poorest pre-placement neighbourhood access, the top 20% of residents ranked by that measure with ties included, so that the group can be larger than 20%; for the bundle, completion among the bottom 20%, the residents who reached the fewest domains before placement, with ties weighted fractionally. These are measures of access, not of income or social disadvantage.
- **Places**: the number of official living zones below the minimum standard (single facilities) and the number of zero-completion living zones, in which no resident completes the bundle, together with the population living in them.

Two further indices assess boundaries. **Boundary-restricted loss** is the decline in the share of residents reaching a facility when residents may use only facilities inside their own unit. **Boundary exposure** is the share of residents whose 15-minute walking catchment crosses a unit boundary.

#### 3.4.2. Analytical approach

The analysis follows the three research questions (Fig. 2). For RQ1, we compute completion curves from 0 to 20 minutes for the three bundles and count living zones by completion. For RQ2, we score every grid-based rule on the three report cards, for seven single facilities and for the bundle, in both years. For RQ3, we apply the zone-based rules to gu, official living zones and dong. For the bundle we add three random partitions of Seoul into 116 contiguous zones and the 116 mobility communities, to separate the effect of the living-zone scale from that of the official boundaries. Because places are counted in official living zones, which favours a standard set on the same zones, we also report how many of each partition's own zones remain empty. To test whether the official boundaries themselves matter, we compare their boundary-restricted loss with that of random partitions that merge contiguous dong into the same number of zones as the plan within each gu, under three generators (population-balanced, dong-balanced and unconstrained; Appendix B). We repeat the test after randomly relocating facilities 20 times. Integer programmes were solved with HiGHS; Appendix A reports solution times and gaps.

## 4. Results

### 4.1. Data overview: service bundles in Seoul's living zones (RQ1)

Seoul's everyday functions are almost universally walkable (Table 3, Fig. 3). Within 15 minutes, 94.8% (2020) and 94.6% (2025) of residents reach all four amenities of Logan et al. (2022), and 73.1% and 77.3% reach all seven everyday categories. Five of the seven categories are within 15 minutes of more than 99% of residents. Among those who do not complete the everyday bundle, 86% and 84% lack only one category. By the standard of everyday functions, Seoul already is a 15-minute city.

The public services that the living-zone plan lists are a different matter. Only 3.7% (2020) and 5.3% (2025) of residents can reach all six domains within 10 minutes, and even at 15 minutes the shares rise only to 20.9% and 27.4%. The gap is not an artefact of the threshold: at the same 10 minutes, 37.2% and 39.9% complete the everyday bundle. Non-completion is also deep rather than marginal. Of the residents who do not complete the bundle, 83% (2020) and 80% (2025) lack two or more domains. Public sports (80% and 77%) and the public library (72% and 70%) are missing most often, whereas childcare is reached by 98% of residents.

What is missing is missing in places. In 50 (2020) and 38 (2025) of the 116 living zones, not a single resident completes the bundle, and in 91 and 73 zones fewer than 5% do. These zero-completion zones are home to 3.82 million (2020) and 2.75 million (2025) residents. In about a third (2025) to more than two-fifths (2020) of Seoul's living zones, no resident can walk within 10 minutes to all six services that the plan lists for them. This is the gap a living-zone plan has to close.

### 4.2. Grid-based placement (RQ2)

#### 4.2.1. Single facilities

Grid-based placement does what it is designed to do (Table 4a, Fig. 4). Access-poor weighting reaches the access-poor better than the living-zone minimum in 12 of 14 facility–year combinations. For libraries in 2025, for example, it reaches 57.9% of them against 53.2% under the living-zone minimum, at an efficiency cost of about 0.1 percentage points. But it barely changes the number of living zones left below the minimum. For libraries, 11 zones remain below it under grid efficiency and 9 under access-poor weighting (2020); for public kindergartens, 14 and 13. Across the seven facilities, access-poor weighting leaves living zones below the minimum for six of them in both years, the exception being senior facilities with 93 additions. Grid placement serves the access-poor well, yet it leaves most under-served living zones under-served.

#### 4.2.2. Service bundle

The same holds, more starkly, for the bundle (Table 4b, Fig. 5, Fig. 6). Solving the bundle maximisation exactly raises completion from 3.7% to 22.8% (2020) and from 5.3% to 24.2% (2025). This is 55% and 47% more than the exact facility-by-facility solution (14.7% and 16.5%), so planning the six domains together pays. Yet 18 (2020) and 14 (2025) living zones still have no resident completing the bundle, home to 1.13 and 0.97 million residents (Fig. 5b). Facility-by-facility planning leaves 21 and 13. The coordinated rule reaches 5.8% and 6.3% of the bottom-20 group, the highest among the grid rules, but leaves 21 and 19 living zones at zero. Whichever grid rule is used, 13 to 21 living zones remain in which no resident completes the bundle. For reference, the stock Seoul actually had in 2025, after its real additions and other changes over the five years, still left 38 living zones at zero.

#### 4.2.3. Why grids leave places empty

The two goals pull in different directions, and the results show why. Completion needs every domain, and four in five non-completers lack two or more domains. A zone that lacks both a library and a sports facility gains no completion from one new library alone. The scarcest additions are those most often missing: 31 libraries and 46 sports facilities for 116 living zones. A person-based objective sends each of them to the cells where it completes the most residents, which are places that already have the other domains. The exact bundle maximisation uses only 177 (2020) and 283 (2025) of the 381 additions, because the rest would complete no further resident, and it reaches only 0.1% and 0.2% of the bottom-20 group. When the objective counts heads, cells that lack many domains are rarely worth completing. Other solutions with the same objective value may exist, but the mechanism does not depend on which is chosen.

For single facilities, the two goals can be reconciled. The hybrid rule, which meets the living-zone minimum first and places the rest with access-poor weights, keeps all but one facility type at zero shortfall and recovers access for the access-poor. For public childcare it reaches 42.6% of them in both years, against 42.6% and 42.8% under access-poor weighting; for public kindergartens, 35.4% and 36.8% against 35.3%. Filling people and filling places are different tasks. The first is done on the grid; the second requires a zone-level standard.

### 4.3. Planning units for minimum standards (RQ3)

#### 4.3.1. Gu

A standard set by gu changes almost nothing (Table 4b, Fig. 6). For the bundle, zero-completion living zones remain at 18 (2020) and 12 (2025) under a 5% gu standard. The standard is binding: 16 (2020) and 14 (2025) gu fall below it before placement, and all of them meet it afterwards. Yet the cost in citywide completion is at most 0.05 percentage points, because a gu can meet its average without reaching the empty living zones inside it. For libraries, the gu standard leaves 10 and 7 living zones below the minimum, almost the same as grid efficiency. Aggregation to gu also hides more of the deficit than smaller units. Averaged over standards from 0.5 to 1.5 times the citywide coverage, the share of under-served residents who live in units that meet the standard on average is 0.21 for dong, 0.34 for living zones and 0.43 for gu (libraries, 2020). The order is the same for all nine facility types examined. Because the units are nested, some of this order follows from aggregation itself; the point is how large the difference is. A gu standard is met on paper while its living zones stay empty.

#### 4.3.2. Dong

A standard set by dong cannot be met with the additions observed. For libraries, meeting the dong standard in every dong requires 58 new libraries in 2025 (proven optimal) and 65–67 in 2020 (the best solution after one hour, gap 3%), against the 31 actually added; living zones require 21 and 18, and gu 2. For the bundle, the solver found no solution that met a 5% dong standard: the best solutions cost 4.6–5.2 percentage points of citywide completion, still left 198–221 of 424 dong below the standard and 155–176 dong with no completer, and did not reduce zero-completion living zones (20 and 16). These bundle runs ended with large gaps (102–9,797%). Minimising only the shortfall did not settle the question either: after two hours the best solutions still left 130–285 dong without a completer, and the lower bound stayed at zero. The bundle runs therefore show that the dong standard was not met within the time limit rather than prove that it cannot be. We also located, for each single facility, the range of zone counts in which a minimum both changes placement and can be met with the observed additions, using random partitions of 25 to 424 zones. The 116-zone scale lies inside that range for four facilities in 2020 (library, cultural facility, public kindergarten and community centre) and three in 2025. The 424-dong scale lies outside it for six of seven facilities in both years. A dong standard spreads the additions too thinly to fill places.

#### 4.3.3. Living zones

Only a standard set at the living-zone scale fills places. For single facilities, the living-zone minimum brings the number of living zones below the minimum to zero for six of seven facilities in both years. The exception, youth centres, has only 11 additions, and the number still falls from 21 to 7 (2020) and from 18 to 8 (2025). For the bundle, a 5% living-zone minimum reduces zero-completion living zones from 18 to 3 (2020) and from 14 to 2 (2025), and zones below 5% from 33 to 9 and from 29 to 5 (Fig. 5c). The residents of zero-completion zones fall from 1.13 to 0.09 million (2020) and from 0.97 to 0.06 million (2025). The cost is 2.8 and 2.1 percentage points of citywide completion, and 1.3 and 0.6 points under a 1% minimum. Bottom-20 completion stays at 0.1–0.4%, about the same as under the grid maximisation.

These runs were stopped at a time limit, so we also asked directly whether every living zone can be filled. When the integer programme minimises only the number of zones without a completer, or only the shortfall from the minimum, it proves for both years that the observed additions can give every official living zone at least one completer and bring every zone up to the 1% and 5% minimums (gap 0; Table A.2). The two or three zones left above are therefore an artefact of solving time, not of the city. Filling every zone has a price. When every zone must meet the 5% minimum, citywide completion can be at most 21.5% (2020) and 22.9% (2025), so the cost is at least 1.3 percentage points in both years. The best complete solutions found within four hours cost 8.4 and 6.9 points, so the exact cost lies between these values.

The effect comes from the scale of the unit. Under the 5% standard, random 116-zone partitions reduce zero-completion official living zones to 5–7 and the mobility communities to 4 (2025), whereas gu and dong do not reduce them at all. Counted in their own zones, every 116-zone partition can be filled: the proof above holds for each of the three random partitions and for the mobility communities (2025), whereas the best dong solutions leave 130 or more dong empty. Because places are mainly counted in official living zones, a standard set on the same zones is favoured in that count, and the ranking among 116-zone partitions should not be read as a test of the official boundaries. The finding is about scale: with the facilities Seoul added, a minimum standard at the scale of its living zones can fill every zone, whereas the same standard set by gu leaves empty zones in place and set by dong was not met.

#### 4.3.4. Official boundaries

Official living zones are not an arbitrary way to draw 116 zones. When residents may use only facilities inside their own zone, the share reaching a library falls by 10.0 percentage points with official boundaries but by 13.9 points (median) with random 116-zone partitions (2020). The difference holds for cultural facilities, kindergartens and childcare, in both years and under all three random generators (p ≤ 0.04). It also survives random relocation of facilities. In all 20 relocations of each of the seven facilities, official boundaries cut less access than the random median, so the result does not depend on where facilities happen to be today. The share of residents whose 15-minute walking catchment crosses a zone boundary is 0.84 for official living zones against 0.89 for random partitions, lower than every one of 40 draws. Finally, a minimum standard set on official living zones reduces shortfalls in the mobility communities, which were not used in placement, more than a standard set on random zones (six of seven facilities in both years). Official living zones cut walkable access less than random partitions of the same number.

### 4.4. Robustness

**Walking threshold.** The main limit of the results is the threshold. Extending it to 12 and 15 minutes raises completion before placement to 11.8% and 27.4% (2025) and reduces zero-completion living zones before placement to 18 and 11. After exact bundle maximisation, 7 and 3 living zones remain at zero, home to 0.45 and 0.09 million residents; facility-by-facility planning leaves 5 and 3. Grid placement still leaves places empty at 12 minutes, roughly the plan's 800 m radius, but at 15 minutes the gap that a zone-level standard closes becomes small. The minimum-standard programmes were run at 10 minutes only. Planning the bundle together still beats facility-by-facility planning in the exact solutions, by 28% at 12 minutes and 8% at 15 minutes.

**Single-facility standards.** For libraries, the minimum number of additions needed to meet a standard in every unit stays far higher for dong than for living zones, and for living zones than for gu, at 10 and 15 minutes, at 3.6 and 4.0 km/h and under four rules for τ. Dong need 45–105 additions against 31–32 available, living zones 9–49 and gu 1–17. Under the strictest rule, the citywide mean, even living zones exceed the budget (44–49), so the feasibility of the living-zone scale holds for practical rather than maximal standards.

**Budget and facility layers.** These variants use the greedy coordinated rule (P = 4), whose gain over greedy facility-by-facility planning is +32% at the observed additions (2020). Halving or doubling the additions changes the size of the gain (+34–35% at half; +17–25% at double) but not its direction. The gain persists when only public sports facilities with verified coordinates are used (+30–34%), when the 2024 urban-planning park layer replaces the 2018 layer (+33%) and when public sports are removed from the bundle (+9–10%). Removing community child centres from the youth and children domain halves completion under the coordinated rule (9.8% and 10.5%), which shows how much the bundle depends on that layer; the gain rises to 56–68%. The place results also hold on the verified sports layer: re-evaluated there, zero-completion living zones number 55 and 41 before placement, 21 and 15 after grid bundle maximisation and 5 and 2 under the 5% living-zone minimum (2020 and 2025).

**Transfer over time.** Sites chosen with 2020 data and evaluated on the 2025 population and network still complete the bundle for 18.0% of residents under the coordinated rule, against 13.1% for facility-by-facility sites.

**Solution quality.** All bundle maximisation and facility-by-facility programmes reached proven optimality, and their solutions were re-evaluated independently with identical results. The bundle minimum-standard programmes were solved within time limits; the 4-hour runs for official living zones ended with gaps of 3–49% (Table A.1). In 2020, 18 zero-completion living zones remained after 1.5 hours under the 1% standard and 4 under the 5% standard, and 3 remained under both after 4 hours. In 2025 the 1.5-hour and 4-hour runs gave the same counts (3 and 2), so the comparison with random partitions and mobility communities, which were run for 1.5 hours, is not driven by solving time. The separate programmes that minimise only the shortfall show that these last zones can be filled (Table A.2). The gu programmes were solved to within 0.1% of optimality and still changed nothing, so the failure of the gu standard is not computational.

**Stability.** When cell populations were multiplied by random log-normal factors (σ = 0.1; ten draws, single facilities), the sites chosen by each rule overlapped substantially (median Jaccard 0.64–1.0), with no systematic difference between grid and zone rules. Zone rules are not more stable than grid rules; their advantage lies in filling places.


## 5. Discussion and conclusion

### 5.1. Why grids leave places empty

This study asked why living zones are needed when accessibility can be measured and facilities located on grids. The first part of the answer is that the gap a living-zone plan must close is a gap in places. Seoul's everyday functions are within a short walk of almost everyone, but the public services its plan lists are not, and in a third to two-fifths of living zones no resident can walk to all six. The second part is that grids, however well optimised, do not close that gap. Placing the same additions on the grid raises citywide completion four- to sixfold, and the coordinated rule reaches the bottom 20% better than any other rule tested for the bundle. Yet 13 to 21 living zones, home to about a million residents, remain in which no resident completes the bundle.

The reason lies in the structure of the problem rather than in the optimiser, as Section 4.2.3 showed. Because completion needs every domain and the scarcest facilities are the ones most often missing, any objective that counts residents sends them to places that already have the other domains. Location research has long noted that maximal coverage favours dense areas over sparse ones (Chanta et al., 2014). Our results show that the same happens between living zones in a dense city, and that it persists when the objective is reshaped to favour cells far from completion. They also extend the warning that average accessibility can mask inequality between people (Willberg et al., 2023; Mouratidis, 2024). Even person-based equity objectives can mask deficits between places, and they do so systematically when services must be used together.

### 5.2. Why living zones, and not gu or dong

The third part of the answer is that only a unit at the scale of the living zone could carry a minimum for every place. A minimum standard set by gu is met on paper while the living zones inside each gu stay empty; it costs almost nothing because it changes almost nothing. A minimum standard set by dong asks for more facilities than the city added, so it spreads them too thinly to fill places. The living-zone scale lies between these limits. It is small enough that a zone's average cannot hide an empty neighbourhood and large enough that the facilities actually added can meet a minimum in every zone. Random partitions with the same number of zones can also fill every one of their own zones (Table A.2), so the scale does most of the work.

The right scale is relative to the facilities available. For libraries, the 31 additions could meet a minimum in every living zone but in no more than about 160 zones, and the 11 youth centres in no more than 80. The 116 living zones fall inside that range for libraries, cultural facilities and kindergartens, whereas for the most plentiful, childcare and senior facilities, a minimum hardly changes placement at 116 zones. A planning unit for minimum standards should therefore be chosen against the number of facilities a city can add, which a city can estimate before it sets its standards.

The official boundaries add to this. They cut walkable access less than random boundaries with the same number of zones, in both years, under three random generators and after random relocation of facilities. This is consistent with the way Seoul drew them, by grouping dong according to local centres and travel linkages (Seoul Metropolitan Government, 2019). A living zone drawn around where people go is also a better container for the services they walk to.

These results connect two literatures that have rarely met. Studies of territorial justice ask whether provision among areas matches need (Davies, 1968; Boyne & Powell, 1991; Hastings, 2007), and minimum standards are a related but distinct principle (Hay, 1995). The place-based policy debate asks when policy should target places rather than people (Barca et al., 2012). Our results add an operational answer to a question these literatures leave open: with the same facilities, a person-based rule and a place-based standard produce different cities, and the place-based standard works only at an intermediate scale. If the goal is that every territory receives at least a minimum, the territory must be drawn at a scale where the minimum is both visible and attainable.

### 5.3. Implications for living-zone and 15-minute city planning

For planning practice the results suggest a division of labour between grids and living zones. Accessibility should be measured, and candidate sites evaluated, on the grid, which is precise and serves people best. Standards and monitoring should be set by living zone, the unit at which a minimum for every place can be both seen and met. A living-zone plan can state a minimum bundle standard for each living zone, meet it first with the facilities to be added and allocate the rest by grid-based efficiency. For single facilities, allocating the rest by access-poor weights also recovered access for the access-poor; for the bundle this remains to be tested, and the living-zone standard alone did little for the bottom 20%. The cost of the first step is modest: in Seoul it is at least 1.3 percentage points of citywide completion under the 5% minimum (0.6 under the 1% minimum in 2025), and solutions that leave only two zones short cost about two. Reporting progress by gu would conceal the zones that remain empty, and setting standards by dong would promise what cannot be delivered.

Implementation needs an owner. In Seoul, living zones have no council or budget of their own; facilities are funded and built by the city and the gu. A living-zone standard can still work as a monitoring and allocation rule. The city can report completion and empty zones by living zone and require gu programmes to address the empty zones within their area first. Because each living zone lies within a single gu, the responsibility is clear.

These implications reach beyond Seoul. Melbourne's 20-minute neighbourhoods, Portland's and Shanghai's x-minute neighbourhoods and China's national hierarchy of life circles all plan daily services by neighbourhood-scale units (Rao et al., 2024; Ministry of Housing and Urban-Rural Development, 2018), although their targets differ, from shares of residents to design standards for new areas. Many 20-minute neighbourhood programmes have not yet set measurable standards (Gower & Grodach, 2022). When zone-level targets were modelled for Melbourne's activity-centre catchments, access improved but new destinations in low-density areas were likely to be underused (Pemberton et al., 2026). Our results add that the scale of the zone decides whether a place-based standard can work: too large and it is met without filling any empty place, too small and it cannot be met. The test can be repeated wherever grid population, facility locations, a street network and planning boundaries are available, which is the most direct next step.

### 5.4. Limitations and future research

Several limitations qualify these conclusions. First, the goal of a minimum in every living zone follows from how Seoul's plan diagnoses and prioritises services, but the plan's priorities guide rather than bind later programmes. If only person-based equity matters, grids suffice, and our results do not then establish the necessity of living zones. Second, the result depends on the threshold. At 10 and 12 minutes grid placement leaves many places empty, but at 15 minutes only three zones remain, and the minimum-standard programmes were run at 10 minutes only. Third, we proved that every living zone can be filled, but not the exact cost of doing so: it lies between 1.3 and 8.4 percentage points (5% minimum), because the programmes that maximise completion under every minimum were stopped at a time limit. The dong programmes also ended without a proof, so the dong result rests on the single-facility solutions and on the bundle runs not finding a solution that met the standard. Fourth, places are counted mainly in official living zones; own-zone counts for the other partitions point the same way, but a count in an independent spatial unit would be stronger. Fifth, for the bundle we did not test the hybrid rule that combines a living-zone standard with access-poor weighting. Sixth, the additions are the observed net increase in occupied cells rather than a cost-based budget, and land availability, facility size, capacity, slope and age-specific demand are not modelled. Seventh, the six-domain bundle and the 10-minute threshold are our operationalisation of the plan; the park and community child centre layers are held fixed, and public sports facilities have coordinates of moderate accuracy. Nor did we test the administrative effort or the costs of coordination between agencies that a living-zone standard may add. Finally, the analysis covers one city at two points in time and does not identify causal effects of past plans. Future research should repeat the test in other cities with different planning units, add capacity and cost to the placement models and examine whether living-zone standards change how residents actually use local services.

### 5.5. Conclusion

Grids fill people, not places. Planning daily services on a fine grid serves residents efficiently and can favour the access-poor, but in Seoul it left whole living zones, home to about a million residents, without the services the living-zone plan lists. Only a minimum standard set at the scale of the living zone could fill all of those places, at a modest cost to citywide access; a standard set by the larger gu hid the gaps, and one set by the smaller dong could not be met with the facilities added. Where a plan aims to leave no living zone without daily public services, a planning unit at that intermediate scale is needed, and neither the grid nor the administrative units above and below it can replace it.

## Appendix A. Integer programmes

**Bundle maximisation (grid).** Let *i* index populated cells with population *p_i* that do not complete the bundle before placement but could complete it, *k* the six domains, *s* the five placed facility types, *j* candidate sites, and *K_i* the domains already reached from *i*. *A^s_ij* = 1 if a facility of type *s* at *j* lies within the threshold of *i*, and *S_k* is the set of placed types that serve domain *k*. With binary siting variables *x_sj* and completion variables *z_i* ∈ [0, 1]:

$$ max Σ_i p_i z_i
$$ subject to z_i ≤ Σ_{s∈S_k} Σ_j A^s_ij x_sj for all i and all k ∉ K_i,
$$ Σ_j x_sj ≤ N_s for all s, x_sj ∈ {0, 1}.   (A.1)

Cells that miss the park domain cannot complete and are excluded. The facility-by-facility benchmark solves, for each *s* separately, max Σ_i p_i y_i subject to y_i ≤ Σ_j A^s_ij x_sj and Σ_j x_sj ≤ N_s.

**Bundle minimum standard (zone).** For a partition into units *u* with population *pop_u* and pre-placement completers *base_u*, add to (A.1)

Σ_{i∈u} p_i z_i + pop_u · d_u ≥ τ_u · pop_u − base_u for all u, with d_u ≥ 0,   (A.2)

and replace the objective by Σ_i p_i z_i − M Σ_u pop_u d_u with *M* = 50, which gives meeting the minimum strong priority over total completion. τ_u = min(τ, τ̄_u), where τ̄_u is the share of residents of *u* in cells that can complete the bundle; τ̄_u never fell below τ.

**Coordinated rule.** At each step, the rule chooses the cell and the facility types placed there that most increase Σ_i p_i (c_i/6)^P, where *c_i* is the number of domains reached from cell *i*; all candidates affected by a placement are re-evaluated exactly before the next step. Table 4b reports *P* = 2, and Section 4.4 the default *P* = 4.

**Proof of feasibility (two stages).** The combined objective of (A.2) mixes total completion with shortfall, which makes the programme hard to solve to optimality. We therefore also solved two simpler problems with the same constraints and additions. Stage 1 drops total completion and minimises either the number of zones with no completer, Σ_u y_u subject to Σ_{i∈u} z_i + y_u ≥ 1 for zones without completers before placement (y_u ∈ {0, 1}), or the total shortfall Σ_u pop_u d_u. Only the cells of the zones concerned are kept, which leaves the optimum unchanged. An optimum of zero proves that every zone can be filled. Stage 2 maximises Σ_i p_i z_i subject to every zone meeting τ_u without shortfall; its upper bound gives a lower bound on the cost of filling every zone. Table A.2 reports the runs.

**Solver settings.** HiGHS via SciPy. Bundle maximisation and facility-by-facility programmes: proven optimal (gap 0) in 0.3–1.4 hours. Zone programmes: time limits of 1.5 hours (gu, dong, random partitions and mobility communities) and 4 hours (official living zones), with a 1.5-hour run of the official living zones for comparison. Table A.1 reports the runs.

**Table A.1.** Bundle minimum-standard programmes: zero-completion official living zones, own-unit zero zones, cost and optimality gap.

| Year | τ | Unit (time limit) | Zero-completion official living zones | Own units with no completer | Cost (percentage points) | Gap |
|---|---|---|---|---|---|---|
| 2020 | 1% | Gu (1.5 h) | 18 | 0 of 25 | 0.02 | 0.1% |
| 2020 | 1% | Dong (1.5 h) | 20 | 158 of 424 | 0.80 | 9,797% |
| 2020 | 1% | Official living zones (1.5 h) | 18 | 18 of 116 | 0.14 | 53% |
| 2020 | 1% | Official living zones (4 h) | 3 | 3 of 116 | 1.30 | 6% |
| 2020 | 5% | Gu (1.5 h) | 18 | 0 of 25 | 0.00 | 0.0% |
| 2020 | 5% | Dong (1.5 h) | 20 | 176 of 424 | 5.18 | 117% |
| 2020 | 5% | Official living zones (1.5 h) | 4 | 4 of 116 | 2.38 | 150% |
| 2020 | 5% | Official living zones (4 h) | 3 | 3 of 116 | 2.80 | 49% |
| 2025 | 1% | Gu (1.5 h) | 13 | 0 of 25 | 0.01 | 0.0% |
| 2025 | 1% | Dong (1.5 h) | 14 | 132 of 424 | 0.57 | 302% |
| 2025 | 1% | Random 116 (1.5 h, 3 draws) | 7–8 | 1–4 of 116 | 0.43–0.56 | 3–5% |
| 2025 | 1% | Mobility communities (1.5 h) | 6 | 4 of 116 | 0.62 | 7% |
| 2025 | 1% | Official living zones (1.5 h) | 3 | 3 of 116 | 0.78 | 6% |
| 2025 | 1% | Official living zones (4 h) | 3 | 3 of 116 | 0.60 | 3% |
| 2025 | 5% | Gu (1.5 h) | 12 | 0 of 25 | 0.05 | 0.1% |
| 2025 | 5% | Dong (1.5 h) | 16 | 155 of 424 | 4.64 | 102% |
| 2025 | 5% | Random 116 (1.5 h, 3 draws) | 5–7 | 0–1 of 116 | 0.98–1.88 | 8–19% |
| 2025 | 5% | Mobility communities (1.5 h) | 4 | 3 of 116 | 2.16 | 28% |
| 2025 | 5% | Official living zones (1.5 h) | 2 | 2 of 116 | 2.31 | 24% |
| 2025 | 5% | Official living zones (4 h) | 2 | 2 of 116 | 2.08 | 21% |

Note: Cost is the loss in citywide completion against the exact bundle maximisation. Gaps refer to the combined objective of Eq. (A.2).


**Table A.2.** Feasibility proofs: minimum number of zones without a completer, minimum shortfall, and maximum completion when every zone meets the minimum.

| Year | Stage and objective | Unit | τ | Result | Bound or gap | Time |
|---|---|---|---|---|---|---|
| 2020 | 1: fewest zones with no completer | Official living zones | – | 0 of 116 | proven (gap 0) | 260 s |
| 2025 | 1: fewest zones with no completer | Official living zones | – | 0 of 116 | proven (gap 0) | 81 s |
| 2025 | 1: fewest zones with no completer | Random 116 (3 draws) | – | 0 of 116 | proven (gap 0) | 120–332 s |
| 2025 | 1: fewest zones with no completer | Mobility communities | – | 0 of 116 | proven (gap 0) | 709 s |
| 2020 | 1: fewest zones with no completer | Dong | – | 285 of 424 (best found) | lower bound 0 | 2 h |
| 2025 | 1: fewest zones with no completer | Dong | – | 130 of 424 (best found) | lower bound 0 | 2 h |
| 2020 | 1: smallest shortfall | Official living zones | 1% | 0 | proven (gap 0) | 174 s |
| 2020 | 1: smallest shortfall | Official living zones | 5% | 0 | proven (gap 0) | 497 s |
| 2025 | 1: smallest shortfall | Official living zones | 1% | 0 | proven (gap 0) | 103 s |
| 2025 | 1: smallest shortfall | Official living zones | 5% | 0 | proven (gap 0) | 256 s |
| 2025 | 1: smallest shortfall | Gu | 5% | 0 | proven (gap 0) | 170 s |
| 2020 | 2: largest completion, every zone ≥ τ | Official living zones | 1% | 15.6% | cost ≥ 1.3 percentage points | 2 h |
| 2020 | 2: largest completion, every zone ≥ τ | Official living zones | 5% | 14.4% | cost ≥ 1.3 percentage points | 4 h |
| 2025 | 2: largest completion, every zone ≥ τ | Official living zones | 1% | 18.5% | cost ≥ 0.6 percentage points | 4 h |
| 2025 | 2: largest completion, every zone ≥ τ | Official living zones | 5% | 17.3% | cost ≥ 1.3 percentage points | 4 h |

Note: Cost is the loss in citywide completion against the exact bundle maximisation (22.8% in 2020 and 24.2% in 2025). Zone counts are re-evaluated on the full grid with the saved sites. The dong shortfall runs (1% and 5%, both years) also ended after 2 h with a lower bound of 0.

## Appendix B. Random partitions and facility relocation

Random partitions keep the number of living zones that the plan assigns to each gu and merge contiguous dong within each gu into that many zones, so that they differ from the official zones only in where the boundaries run. Three generators were used: population-balanced, dong-balanced and unconstrained region growing. For the boundary-restricted loss we drew 150 population-balanced partitions once, on the 2020 dong graph, and evaluated the same partitions in both years; the significance tests compare the official zones with these 150 and with 100 partitions from each of the other two generators. The p-value is the share of random partitions whose loss is lower than that of the official living zones. For relocation, the facilities of each type were redrawn 20 times at random among their candidate and existing cells, keeping their number, and losses were recomputed for the official boundaries and for the median of ten random partitions. Boundary exposure was compared with 40 random partitions.

## References

Abbiasov, T., Heine, C., Sabouri, S., Salazar-Miranda, A., Santi, P., Glaeser, E., & Ratti, C. (2024). The 15-minute city quantified using human mobility data. *Nature Human Behaviour*, *8*(3), 445–455. https://doi.org/10.1038/s41562-023-01770-y

Allam, Z., Nieuwenhuijsen, M., Chabaud, D., & Moreno, C. (2022). The 15-minute city offers a new framework for sustainability, liveability, and health. *The Lancet Planetary Health*, *6*(3), e181–e183. https://doi.org/10.1016/S2542-5196(22)00014-6

Arslan, O., & Laporte, G. (2025). The 15-minute city concept: An operations research perspective and a research agenda. *Transportation Research Part E: Logistics and Transportation Review*, *202*, Article 104287. https://doi.org/10.1016/j.tre.2025.104287

Barca, F., McCann, P., & Rodríguez-Pose, A. (2012). The case for regional development intervention: Place-based versus place-neutral approaches. *Journal of Regional Science*, *52*(1), 134–152. https://doi.org/10.1111/j.1467-9787.2011.00756.x

Batta, R., Lejeune, M., & Prasad, S. (2014). Public facility location using dispersion, population, and equity criteria. *European Journal of Operational Research*, *234*(3), 819–829. https://doi.org/10.1016/j.ejor.2013.10.032

Bertsimas, D., Farias, V. F., & Trichakis, N. (2011). The price of fairness. *Operations Research*, *59*(1), 17–31. https://doi.org/10.1287/opre.1100.0865

Boyne, G., & Powell, M. (1991). Territorial justice: A review of theory and evidence. *Political Geography Quarterly*, *10*(3), 263–281. https://doi.org/10.1016/0260-9827(91)90038-V

Bruno, M., Monteiro Melo, H. P., Campanelli, B., & Loreto, V. (2024). A universal framework for inclusive 15-minute cities. *Nature Cities*, *1*(10), 633–641. https://doi.org/10.1038/s44284-024-00119-4

Calafiore, A., Dunning, R., Nurse, A., & Singleton, A. (2022). The 20-minute city: An equity analysis of Liverpool City Region. *Transportation Research Part D: Transport and Environment*, *102*, Article 103111. https://doi.org/10.1016/j.trd.2021.103111

Chanta, S., Mayorga, M. E., & McLay, L. A. (2014). Improving emergency service in rural areas: A bi-objective covering location model for EMS systems. *Annals of Operations Research*, *221*(1), 133–159. https://doi.org/10.1007/s10479-011-0972-6

Chau, H.-W., Gilzean, I., Jamei, E., Palmer, L., Preece, T., & Quirke, M. (2022). Comparative analysis of 20-minute neighbourhood policies and practices in Melbourne and Scotland. *Urban Planning*, *7*(4). https://doi.org/10.17645/up.v7i4.5668

Chen, L., Zeng, H., Wu, L., Tian, Q., Zhang, N., He, R., Xue, H., Zheng, J., Liu, J., Liang, F., & Zhu, B. (2023). Spatial accessibility evaluation and location optimization of primary healthcare in China: A case study of Shenzhen. *GeoHealth*, *7*(5), Article e2022GH000753. https://doi.org/10.1029/2022GH000753

Church, R., & ReVelle, C. (1974). The maximal covering location problem. *Papers of the Regional Science Association*, *32*(1), 101–118. https://doi.org/10.1007/BF01942293

Cranshaw, J., Schwartz, R., Hong, J., & Sadeh, N. (2012). The Livehoods project: Utilizing social media to understand the dynamics of a city. *Proceedings of the International AAAI Conference on Web and Social Media*, *6*(1), 58–65. https://doi.org/10.1609/icwsm.v6i1.14278

Current, J. R., & Schilling, D. A. (1990). Analysis of errors due to demand data aggregation in the set covering and maximal covering location problems. *Geographical Analysis*, *22*(2), 116–126. https://doi.org/10.1111/j.1538-4632.1990.tb00199.x

Davies, B. (1968). *Social needs and resources in local services: A study of variations in standards of provision of personal social services between local authority areas*. Michael Joseph.

Elldér, E. (2024). The 15-minute city dilemma? Balancing local accessibility and gentrification in Gothenburg, Sweden. *Transportation Research Part D: Transport and Environment*, *135*, Article 104360. https://doi.org/10.1016/j.trd.2024.104360

Ferrer-Ortiz, C., Marquet, O., Mojica, L., & Vich, G. (2022). Barcelona under the 15-minute city lens: Mapping the accessibility and proximity potential based on pedestrian travel times. *Smart Cities*, *5*(1), 146–161. https://doi.org/10.3390/smartcities5010010

Fotheringham, A. S., & Wong, D. W. S. (1991). The modifiable areal unit problem in multivariate statistical analysis. *Environment and Planning A: Economy and Space*, *23*(7), 1025–1044. https://doi.org/10.1068/a231025

Francis, R. L., Lowe, T. J., Rayco, M. B., & Tamir, A. (2009). Aggregation error for location models: Survey and analysis. *Annals of Operations Research*, *167*(1), 171–208. https://doi.org/10.1007/s10479-008-0344-z

Gao, F., Kihal, W., Le Meur, N., Souris, M., & Deguen, S. (2017). Does the edge effect impact on the measure of spatial accessibility to healthcare providers? *International Journal of Health Geographics*, *16*(1), Article 46. https://doi.org/10.1186/s12942-017-0119-3

Gower, A., & Grodach, C. (2022). Planning innovation or city branding? Exploring how cities operationalise the 20-minute neighbourhood concept. *Urban Policy and Research*, *40*(1), 36–52. https://doi.org/10.1080/08111146.2021.2019701

Ha, J., & Lee, S. (2016). A study on the designation of living zones by its spatial hierarchy using OD data and community detection technique: Focused on the 2010 household travel survey data of the Seoul Metropolitan Area. [In Korean] *Journal of Korea Planning Association*, *51*(6), 79–98. https://doi.org/10.17208/jkpa.2016.11.51.6.79

Ha, J., Kim, Y., & Lee, S. (2024). Analysis of functional living zones changes and influencing factors of travel distance before and after COVID-19 in Seoul, Korea: Using mobile phone-based mobility bigdata and community detection. [In Korean] *Journal of Korea Planning Association*, *59*(2), 73–92. https://doi.org/10.17208/jkpa.2024.04.59.2.73

Hastings, A. (2007). Territorial justice and neighbourhood environmental services: A comparison of provision to deprived and better-off neighbourhoods in the UK. *Environment and Planning C: Government and Policy*, *25*(6), 896–917. https://doi.org/10.1068/c0657

Hay, A. M. (1995). Concepts of equity, fairness and justice in geographical studies. *Transactions of the Institute of British Geographers*, *20*(4), 500. https://doi.org/10.2307/622979

Hewko, J., Smoyer-Tomic, K. E., & Hodgson, M. J. (2002). Measuring neighbourhood spatial accessibility to urban amenities: Does aggregation error matter? *Environment and Planning A: Economy and Space*, *34*(7), 1185–1206. https://doi.org/10.1068/a34171

Hillsman, E. L., & Rhoda, R. (1978). Errors in measuring distances from populations to service centers. *The Annals of Regional Science*, *12*(3), 74–88. https://doi.org/10.1007/BF01286124

Hipp, J. R., & Boessen, A. (2013). Egohoods as waves washing across the city: A new measure of "neighborhoods". *Criminology*, *51*(2), 287–327. https://doi.org/10.1111/1745-9125.12006

Hooghe, L., & Marks, G. (2003). Unraveling the central state, but how? Types of multi-level governance. *American Political Science Review*, *97*(2), 233–243. https://doi.org/10.1017/S0003055403000649

Horton, D., Logan, T. M., Speakman, E., & Skipper, D. (2025). Hundreds of grocery outlets needed across the United States to achieve walkable cities. *Nature Communications*, *16*(1), Article 6051. https://doi.org/10.1038/s41467-025-61454-1

Horton, D., Murrell, J., Skipper, D., Speakman, E., & Logan, T. (2025). A scalable optimization approach for equitable facility location: Methodology and transportation applications. *Transportation Research Part B: Methodological*, *201*, Article 103319. https://doi.org/10.1016/j.trb.2025.103319

Huang, W., & Khalil, E. B. (2023). Walkability optimization: Formulations, algorithms, and a case study of Toronto. *Proceedings of the AAAI Conference on Artificial Intelligence*, *37*(12), 14249–14258. https://doi.org/10.1609/aaai.v37i12.26667

Jafari, A., Singh, D., & Giles-Corti, B. (2023). Residential density and 20-minute neighbourhoods: A multi-neighbourhood destination location optimisation approach. *Health & Place*, *83*, Article 103070. https://doi.org/10.1016/j.healthplace.2023.103070

Jasso Chávez, J. A., Kelly, N., Pereira, R. H. M., Boisjoly, G., & Manaugh, K. (2026). Revisiting sufficientarianism in accessibility research: A review of accessibility poverty. *Transport Reviews*. Advance online publication, 1–29. https://doi.org/10.1080/01441647.2026.2720413

Jiao, H., & Xiao, M. (2022). Delineating urban community life circles for large Chinese cities based on mobile phone data and POI data—The case of Wuhan. *ISPRS International Journal of Geo-Information*, *11*(11), Article 548. https://doi.org/10.3390/ijgi11110548

Karsu, Ö., & Morton, A. (2015). Inequity averse optimization in operational research. *European Journal of Operational Research*, *245*(2), 343–359. https://doi.org/10.1016/j.ejor.2015.02.035

Khavarian-Garmsir, A. R., Sharifi, A., Hajian Hossein Abadi, M., & Moradi, Z. (2023). From garden city to 15-minute city: A historical perspective and critical assessment. *Land*, *12*(2), Article 512. https://doi.org/10.3390/land12020512

Kim, Y., Oh, J., & Kim, S. (2020). The transition from traditional infrastructure to Living SOC and its effectiveness for community sustainability: The case of South Korea. *Sustainability*, *12*(24), Article 10227. https://doi.org/10.3390/su122410227

Kline, P., & Moretti, E. (2014). People, places, and public policy: Some simple welfare economics of local economic development programs. *Annual Review of Economics*, *6*(1), 629–662. https://doi.org/10.1146/annurev-economics-080213-041024

Kwan, M.-P. (2012). The uncertain geographic context problem. *Annals of the Association of American Geographers*, *102*(5), 958–968. https://doi.org/10.1080/00045608.2012.687349

Lawhon, L. L. (2009). The neighborhood unit: Physical design or physical determinism? *Journal of Planning History*, *8*(2), 111–132. https://doi.org/10.1177/1538513208327072

Liu, T., & Chai, Y. (2015). Daily life circle reconstruction: A scheme for sustainable development in urban China. *Habitat International*, *50*, 250–260. https://doi.org/10.1016/j.habitatint.2015.08.038

Logan, T., Hobbs, M., Conrow, L., Reid, N., Young, R., & Anderson, M. (2022). The x-minute city: Measuring the 10, 15, 20-minute city and an evaluation of its use for sustainable urban design. *Cities*, *131*, Article 103924. https://doi.org/10.1016/j.cities.2022.103924

Lucas, K., van Wee, B., & Maat, K. (2016). A method to evaluate equitable accessibility: Combining ethical theories and accessibility-based approaches. *Transportation*, *43*(3), 473–490. https://doi.org/10.1007/s11116-015-9585-2

Ma, W., Wang, N., Li, Y., & Sun, D. (2023). 15-min pedestrian distance life circle and sustainable community governance in Chinese metropolitan cities: A diagnosis. *Humanities and Social Sciences Communications*, *10*(1), Article 364. https://doi.org/10.1057/s41599-023-01812-w

Mandell, M. B. (1991). Modelling effectiveness-equity trade-offs in public service delivery systems. *Management Science*, *37*(4), 467–482. https://doi.org/10.1287/mnsc.37.4.467

Marchigiani, E., & Bonfantini, B. (2022). Urban transition and the return of neighbourhood planning. Questioning the proximity syndrome and the 15-minute city. *Sustainability*, *14*(9), Article 5468. https://doi.org/10.3390/su14095468

Marsh, M. T., & Schilling, D. A. (1994). Equity measurement in facility location analysis: A review and framework. *European Journal of Operational Research*, *74*(1), 1–17. https://doi.org/10.1016/0377-2217(94)90200-3

Martens, K. (2016). *Transport justice: Designing fair transportation systems*. Routledge. https://doi.org/10.4324/9781315746852

Ministry of Housing and Urban-Rural Development. (2018). *Standard for urban residential area planning and design* (GB 50180-2018) [in Chinese]. Announcement No. 142, 10 July 2018. http://www.moe.gov.cn/jyb_xwfb/xw_zt/moe_357/jyzt_2019n/2019_zt13/zcwj/201906/t20190606_384732.html

Moreno, C., Allam, Z., Chabaud, D., Gall, C., & Pratlong, F. (2021). Introducing the “15-minute city”: Sustainability, resilience and place identity in future post-pandemic cities. *Smart Cities*, *4*(1), 93–111. https://doi.org/10.3390/smartcities4010006

Mouratidis, K. (2024). Time to challenge the 15-minute city: Seven pitfalls for sustainability, equity, livability, and spatial analysis. *Cities*, *153*, Article 105274. https://doi.org/10.1016/j.cities.2024.105274

Murray, A. T. (2016). Maximal coverage location problem: Impacts, significance, and evolution. *International Regional Science Review*, *39*(1), 5–27. https://doi.org/10.1177/0160017615600222

Nicoletti, L., Sirenko, M., & Verma, T. (2023). Disadvantaged communities have lower access to urban infrastructure. *Environment and Planning B: Urban Analytics and City Science*, *50*(3), 831–849. https://doi.org/10.1177/23998083221131044

Office for Government Policy Coordination. (2019, April 15). *Gyms and libraries within 10 minutes anywhere: KRW 30 trillion for Life SOC* [in Korean]. Korea Policy Briefing. https://www.korea.kr/news/policyNewsView.do?newsId=148860006

Olivari, B., Cipriano, P., Napolitano, M., & Giovannini, L. (2023). Are Italian cities already 15-minute? Presenting the Next Proximity Index: A novel and scalable way to measure it, based on open data. *Journal of Urban Mobility*, *4*, Article 100057. https://doi.org/10.1016/j.urbmob.2023.100057

Openshaw, S. (1984). *The modifiable areal unit problem* (Concepts and Techniques in Modern Geography No. 38). Geo Books.

Papadopoulos, E., Sdoukopoulos, A., & Politis, I. (2023). Measuring compliance with the 15-minute city concept: State-of-the-art, major components and further requirements. *Sustainable Cities and Society*, *99*, Article 104875. https://doi.org/10.1016/j.scs.2023.104875

Park, J., Eom, S., & Lee, M.-H. (2026). Benchmarking living-zone plans with mobility community detection: Evidence from Seoul's mobile-phone-based mobility data. *Journal of Transport Geography*, *135*, Article 104753. https://doi.org/10.1016/j.jtrangeo.2026.104753

Park, J., Lee, J. W., & Lee, H. C. (2023). A study on the accessibility and edge effect in Life-SOC (social overhead capital) allocation: A case study of Seoul Plan 2030 living-area (neighborhood) planning. [In Korean] *Journal of the Urban Design Institute of Korea Urban Design*, *24*(3), 137–155. https://doi.org/10.38195/judik.2023.06.24.3.137

Park, Y., & Rogers, G. O. (2015). Neighborhood planning theory, guidelines, and research: Can area, population, and boundary guide conceptual framing? *Journal of Planning Literature*, *30*(1), 18–36. https://doi.org/10.1177/0885412214549422

Pemberton, S., Saghapour, T., Giles-Corti, B., Abdollahyar, M., Both, A., Pearson, D., Higgs, C., Jafari, A., Singh, D., Gunn, L., Woodcock, J., & Zapata-Diomedi, B. (2026). Infrastructure and accessibility implications of implementing x-minute city policies in low-density contexts. *Cities*, *171*, Article 106717. https://doi.org/10.1016/j.cities.2025.106717

Pereira, R. H. M., Schwanen, T., & Banister, D. (2017). Distributive justice and equity in transportation. *Transport Reviews*, *37*(2), 170–191. https://doi.org/10.1080/01441647.2016.1257660

Perry, C. A. (1929). The neighborhood unit. In *Neighborhood and community planning* (Regional Survey of New York and Its Environs, Vol. 7, Monograph 1). Regional Plan of New York and Its Environs.

Purcell, M. (2006). Urban democracy and the local trap. *Urban Studies*, *43*(11), 1921–1941. https://doi.org/10.1080/00420980600897826

Qi, L., Harumain, Y. A. S., & Dali, M. M. (2025). Enhancing sustainability: A systematic review of the livable neighborhood life circle and its prospects in China. *Sustainability*, *17*(19), Article 8813. https://doi.org/10.3390/su17198813

Rao, F., Kong, Y., Ng, K. H., Xie, Q., & Zhu, Y. (2024). Unravelling the spatial arrangement of the 15-minute city: A comparative study of Shanghai, Melbourne, and Portland. *Planning Theory & Practice*, *25*(2), 184–206. https://doi.org/10.1080/14649357.2024.2350948

Ratti, C., Sobolevsky, S., Calabrese, F., Andris, C., Reades, J., Martino, M., Claxton, R., & Strogatz, S. H. (2010). Redrawing the map of Great Britain from a network of human interactions. *PLoS ONE*, *5*(12), Article e14248. https://doi.org/10.1371/journal.pone.0014248

Şahin, G., & Süral, H. (2007). A review of hierarchical facility location models. *Computers & Operations Research*, *34*(8), 2310–2331. https://doi.org/10.1016/j.cor.2005.09.005

Seoul Metropolitan Government. (2018, March 7). *Our neighbourhood's future: Living zone plans for 116 areas announced* [in Korean]. Seoul Information Communication Plaza. https://opengov.seoul.go.kr/mediahub/14781653

Seoul Metropolitan Government. (2019). *2030 Seoul living zone plan white paper* [in Korean]. Seoul Metropolitan Government. ISBN 979-11-6161-147-1

Sharifi, A. (2016). From garden city to eco-urbanism: The quest for sustainable neighborhood development. *Sustainable Cities and Society*, *20*, 1–16. https://doi.org/10.1016/j.scs.2015.09.002

Shin, J., Newman, G. D., & Park, Y. (2024). Urban versus rural disparities in amenity proximity and housing price: The case of integrated urban–rural city, Sejong, South Korea. *Journal of Housing and the Built Environment*, *39*(2), 727–747. https://doi.org/10.1007/s10901-023-10098-y

Staricco, L. (2022). 15-, 10- or 5-minute city? A focus on accessibility to services in Turin, Italy. *Journal of Urban Mobility*, *2*, Article 100030. https://doi.org/10.1016/j.urbmob.2022.100030

Stępniak, M., & Jacobs-Crisioni, C. (2017). Reducing the uncertainty induced by spatial aggregation in accessibility and spatial interaction applications. *Journal of Transport Geography*, *61*, 17–29. https://doi.org/10.1016/j.jtrangeo.2017.04.001

Sun, Y., & Thakuriah, P. (2021). Public transport availability inequalities and transport poverty risk across England. *Environment and Planning B: Urban Analytics and City Science*, *48*(9), 2775–2789. https://doi.org/10.1177/2399808321991536

Talen, E., & Anselin, L. (1998). Assessing spatial equity: An evaluation of measures of accessibility to public playgrounds. *Environment and Planning A: Economy and Space*, *30*(4), 595–613. https://doi.org/10.1068/a300595

Tao, Z., Cheng, Y., Zheng, Q., & Li, G. (2018). Measuring spatial accessibility to healthcare services with constraint of administrative boundary: A case study of Yanqing District, Beijing, China. *International Journal for Equity in Health*, *17*(1), Article 7. https://doi.org/10.1186/s12939-018-0720-5

Vale, D., & Lopes, A. S. (2023). Accessibility inequality across Europe: A comparison of 15-minute pedestrian accessibility in cities with 100,000 or more inhabitants. *npj Urban Sustainability*, *3*(1), Article 55. https://doi.org/10.1038/s42949-023-00133-w

van der Veen, A. S., Annema, J. A., Martens, K., van Arem, B., & Correia, G. H. d. A. (2020). Operationalizing an indicator of sufficient accessibility – A case study for the city of Rotterdam. *Case Studies on Transport Policy*, *8*(4), 1360–1370. https://doi.org/10.1016/j.cstp.2020.09.007

Ville de Paris. (n.d.). *Paris ville du quart d'heure, ou le pari de la proximité*. Retrieved October 1, 2026, from https://www.paris.fr/dossiers/paris-ville-du-quart-d-heure-ou-le-pari-de-la-proximite-37

Weng, M., Ding, N., Li, J., Jin, X., Xiao, H., He, Z., & Su, S. (2019). The 15-minute walkable neighborhoods: Measurement, social inequalities and implications for building healthy communities in urban China. *Journal of Transport & Health*, *13*, 259–273. https://doi.org/10.1016/j.jth.2019.05.005

Willberg, E., Fink, C., & Toivonen, T. (2023). The 15-minute city for all? – Measuring individual and temporal variations in walking accessibility. *Journal of Transport Geography*, *106*, Article 103521. https://doi.org/10.1016/j.jtrangeo.2022.103521

Wu, H., Wang, L., Zhang, Z., & Gao, J. (2021). Analysis and optimization of 15-minute community life circle based on supply and demand matching: A case study of Shanghai. *PLOS ONE*, *16*(8), Article e0256904. https://doi.org/10.1371/journal.pone.0256904

Wu, Y., & Zhang, W. (2026). Is a life circle a circle? Topological data analysis on activity space delineation. *Annals of the American Association of Geographers*, *116*(7), 1600–1624. https://doi.org/10.1080/24694452.2025.2608173

Xu, Y., Olmos, L. E., Abbar, S., & González, M. C. (2020). Deconstructing laws of accessibility and facility distribution in cities. *Science Advances*, *6*(37), Article eabb4112. https://doi.org/10.1126/sciadv.abb4112

Yang, C., & Qian, Z. (2024). The new paradigm of future cities? Facilitating dialogues between the 15-minute city and the 15-minute life circle in China based on a bibliometric analysis. *Transactions in Planning and Urban Research*, *3*(3), 294–312. https://doi.org/10.1177/27541223241274491

Zhai, S., Kong, Y., Song, G., & Luo, J. (2023). A new facility location problem for urban public facility planning toward 15-minute life circle: Model and experiment [in Chinese]. *Acta Geographica Sinica*, *78*(6), 1484–1497. https://doi.org/10.11821/dlxb202306010

## Figure captions

**Fig. 1.** Study area: Seoul's 25 gu, 116 official living zones and 424 administrative dong.

**Fig. 2.** Analytical framework. The same facility additions (net increase 2020–2025) are placed under grid-based and zone-based rules and scored on three report cards.

**Fig. 3.** Bundle completion. (a, b) Share of residents completing each bundle by walking time, 2020 and 2025; dotted lines mark 10 and 15 minutes. (c) Number of missing domains among residents who do not complete the bundle, 2025.

**Fig. 4.** Official living zones below the minimum standard after placing the observed additions of each facility, by placement rule. (a) 2020, (b) 2025. Facility inventories refer to 31 December 2019 and 2024, except public kindergartens (1 October), community service centres (30 June 2019 and 31 July 2024) and cultural facilities (1 January 2020 and 2025).

**Fig. 5.** Share of residents completing the six-domain bundle within 10 minutes, by official living zone, 2025. (a) Before placement; (b) after grid bundle maximisation; (c) after placement under a 5% living-zone minimum standard.

**Fig. 6.** Zero-completion official living zones after placing the 381 additions under each rule, (a) 2020 and (b) 2025. Random and mobility-community partitions were run for 2025 only.

## Tables

- Table 1. Planning hierarchy of Seoul.
- Table 2. Planned public-service bundle: domains, facility cells and placement budget.
- Table 3. Bundle completion rate by walking-time threshold.
- Table 4. Three report cards by placement rule: (a) single facilities, (b) six-domain bundle.
- Table A.1. Bundle minimum-standard programmes (Appendix A).
- Table A.2. Feasibility proofs (Appendix A).
