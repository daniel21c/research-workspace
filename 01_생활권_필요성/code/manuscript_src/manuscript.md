# Grids fill people, not places: Testing the necessity of living zones for walkable public services in Seoul

## Abstract

Cities increasingly plan daily life through living zones, such as neighbourhood units, life circles and 15-minute neighbourhoods, that differ from their administrative districts. Yet walking accessibility can be measured, and facilities located, on fine grids, so why are living zones needed? We test this empirically in Seoul, whose 2030 Living Zone Plan promises daily public services in each of its 116 living zones. Using a 100 m population grid, street-network walking times and facility records for 2020 and 2025, we measure whether residents can walk to all six planned service domains within 10 minutes. We then place the facilities actually added over five years under grid-based rules and under minimum standards set by gu (district), living zone or dong (neighbourhood). Only 3.7–5.3% of residents reach all six domains, and in 38–50 living zones no resident does. Grid-based placement fills people but not places: it raises citywide completion to 24% and best serves deprived residents, yet leaves 14–21 living zones where no resident completes the bundle. A minimum standard at the living-zone scale reduces such zones from 14 to 2 at a cost of about two percentage points of citywide completion. The same standard set by gu changes almost nothing, and set by dong it cannot be met with the facilities added. Official living-zone boundaries also cut walkable access less than random partitions with the same number of zones (p ≤ 0.04). Living zones are therefore necessary to fill every place with daily public services.

**Keywords:** Living zone; 15-minute city; Walking accessibility; Minimum service standard; Facility location; Planning unit; Seoul

## 1. Introduction

Planning walkable, self-contained neighbourhoods has returned to the centre of urban policy. The most visible expression is the 15-minute city, which asks that the services residents need every day lie within a short walk or cycle of home (Moreno et al., 2021; Allam et al., 2022). Paris has made it a municipal programme (Ville de Paris, n.d.), Melbourne plans by 20-minute neighbourhoods (Chau et al., 2022), and Shanghai, Melbourne and Portland have each written x-minute neighbourhoods into their plans (Rao et al., 2024). In China, Shanghai's 2016 planning guidance introduced the 15-minute community life circle, a walkable area equipped with basic daily services and public space (Wu et al., 2021), and the national standard for residential areas now organises planning by 15-, 10- and 5-minute life circles (Ministry of Housing and Urban-Rural Development, 2018). Korea's Life SOC programme promises gyms, libraries and childcare "within ten minutes" of home (Office for Government Policy Coordination, 2019; Kim et al., 2020). A growing literature measures how far real cities fall short of these goals (Logan et al., 2022; Papadopoulos et al., 2023; Willberg et al., 2023).

What these programmes share is a planning unit. They plan and promise daily services by living zones: territories smaller than a city and larger than a block, which are often not the city's administrative districts. The idea goes back to Perry's (1929) neighbourhood unit, which sized a residential area by the walking catchment of an elementary school and equipped it with shops, parks and community facilities (Lawhon, 2009; Park & Rogers, 2015). Researchers now go further and delineate living zones from data rather than from administrative maps, using mobile-phone, GPS and travel-survey flows (Ratti et al., 2010; Ha & Lee, 2016; Jiao & Xiao, 2022; Park et al., 2026; Wu & Zhang, 2026). Seoul's 2030 Living Zone Plan is a leading example. It divides the city into 116 local living zones that group neighbouring administrative units, and it commits to supplying a common set of daily public services in each of them (Seoul Metropolitan Government, 2018, 2019).

Yet the same tools that made these ideas measurable have also made the living zone look redundant. Walking accessibility can now be computed cell by cell on fine grids, which avoids the aggregation errors of zone-based measures (Hewko et al., 2002; Stępniak & Jacobs-Crisioni, 2017). Facilities can be located on the same grid by optimisation models that maximise coverage or favour the worst-off (Church & ReVelle, 1974; Marsh & Schilling, 1994). Critics argue that fixed, non-overlapping neighbourhood boundaries are a flawed way to describe where people live (Hipp & Boessen, 2013). And the 15-minute city has been criticised for stating goals without specifying the means to reach them (Khavarian-Garmsir et al., 2023); most cities that adopt 20-minute neighbourhoods lack measurable standards or statutory force to implement them (Gower & Grodach, 2022). If the grid can both diagnose and fix, why plan through living zones? Previous studies have asked whether living-zone boundaries match the communities residents form through their daily trips (Ha et al., 2024; Park et al., 2026), and how boundaries affect the supply of local facilities (Park et al., 2023). They have not asked whether the living zone itself is necessary.

This paper tests that necessity empirically. Our argument is that the answer depends on what a living-zone plan promises. Seoul's plan does not only promise that more people will reach services. It promises that every living zone will be supplied, which is a promise about places as well as people (Davies, 1968; Boyne & Powell, 1991). Living zones are necessary if, and only if, three conditions hold. Planning on the grid must fail to fill every zone. A minimum standard set at the living-zone scale must succeed. And neither the larger district nor the smaller neighbourhood unit can do the same job.

We test these conditions in Seoul, one of the few cities whose population grid, facility registers, street network, mobility flows and official living-zone boundaries are all publicly available. Using a 100 m population grid, walking times on the street network and facility records for 2020 and 2025, we measure whether residents can walk to all six public-service domains of Seoul's plan within 10 minutes. We then place the facilities that Seoul actually added between 2020 and 2025 under grid-based and zone-based rules. Three research questions (RQs) structure the analysis:

- **RQ1**: How completely do Seoul's living zones provide the bundle of daily public services that the living-zone plan promises, compared with everyday commercial functions?
- **RQ2**: Can grid-based facility placement, whether it maximises total access or prioritises deprived residents, fill every living zone?
- **RQ3**: At which planning unit (gu, living zone or dong) can a zone-level minimum standard be met with the facilities actually added, and do the official living-zone boundaries matter?

The paper makes three contributions. First, it measures, zone by zone, the completeness of the public-service bundle that living-zone plans promise, rather than the everyday amenities that most 15-minute city studies count. Second, it shows with exact optimisation that grid-based placement fills people but leaves living zones empty, and explains why. Third, it compares minimum standards set by district, living zone and neighbourhood under the same facility additions. Only the living-zone scale fills every place, which gives the living zone an empirical rather than an assumed role in planning.

## 2. Literature review

### 2.1. Defining and contextualising living zones

The living zone descends from the neighbourhood unit. Perry (1929) bounded a residential neighbourhood by the walking catchment of an elementary school, placed shops at its edge and community facilities at its centre, and made the unit the basis for counting and supplying daily services. Later movements, from the garden city to new urbanism and eco-urbanism, revised the area, population and boundary of such units but kept the idea that daily life should be planned within them (Sharifi, 2016; Park & Rogers, 2015). The concept has been criticised as physical determinism, although historians argue that it was a design model for arranging facilities and opportunities for contact rather than a tool of social engineering (Lawhon, 2009). The 15-minute city inherits both the idea and the critique (Khavarian-Garmsir et al., 2023; Marchigiani & Bonfantini, 2022).

East Asian planning has turned the neighbourhood unit into an explicit hierarchy of living zones. In Chinese cities, the life circle was first proposed to restructure daily activity spaces that had become scattered after the end of the work-unit system (Liu & Chai, 2015). It then became a planning paradigm, with Shanghai's 2016 guidance and a national standard of 15-, 10- and 5-minute life circles (Ministry of Housing and Urban-Rural Development, 2018; Yang & Qian, 2024; Qi et al., 2025). Empirical studies find that service provision in these life circles is uneven, with high convenience in central districts and shortfalls in the suburbs (Weng et al., 2019; Wu et al., 2021; Ma et al., 2023). In Korea, the Life SOC programme set minimum provision standards for daily facilities, such as an elementary school within a 15-minute walk (Shin et al., 2024). Its supply has been evenly distributed among regions, but with little attention to the distance between facilities and homes (Kim et al., 2020). Seoul's 2030 Living Zone Plan formalised the hierarchy at two levels, five regional and 116 local living zones, and made the local living zone the unit in which daily public services are diagnosed and supplied (Seoul Metropolitan Government, 2018, 2019).

A second strand of research asks where living zones should be drawn. Interaction data have been used to redraw regions from telephone networks (Ratti et al., 2010), to identify neighbourhoods from social-media check-ins (Cranshaw et al., 2012) and to delineate life circles from mobile-phone and point-of-interest data (Jiao & Xiao, 2022; Wu & Zhang, 2026). In Seoul, community detection on travel flows has been used to derive functional living zones and to benchmark the official ones (Ha & Lee, 2016; Ha et al., 2024; Park et al., 2026). These studies find that data-derived zones often overlap with administrative ones but are irregular in shape, and that neighbouring zones share facilities (Ratti et al., 2010; Jiao & Xiao, 2022). They take the need for living zones as given and ask how to draw them.

Why should services be planned by territory rather than by person? The planning and public-finance literatures give normative reasons. Territorial justice holds that public services should be distributed among areas in proportion to their needs, so that no area is left without a basic level of provision (Davies, 1968; Boyne & Powell, 1991), and studies of neighbourhood services show that provision often fails this test (Hastings, 2007). Fiscal equivalence holds that the territory of a decision should match the territory of the people who benefit from it (Olson, 1969). Theories of multi-level governance add that task-specific jurisdictions can sit alongside general-purpose ones (Hooghe & Marks, 2003), and the debate on place-based policy asks when interventions should target places rather than people (Barca et al., 2012; Kline & Moretti, 2014). None of these arguments is empirical in itself. Each states a goal for which an intermediate unit may or may not be required.

Choosing a unit also shapes what can be seen. The modifiable areal unit problem means that the same pattern produces different results at different scales and zonings (Openshaw, 1984; Fotheringham & Wong, 1991). The uncertain geographic context problem warns that residents' actual exposure rarely matches administrative boundaries (Kwan, 2012). For accessibility, boundaries cut off services that residents can reach across them (Tao et al., 2018; Gao et al., 2017), and in Seoul the supply of local facilities planned for a living zone changes with how the zone is drawn (Park et al., 2023). These problems are usually treated as sources of error. Here they become the object of study, because a unit that hides deficits cannot be used to promise their removal.

### 2.2. Walkable service bundles and grid-based location planning

Research on the 15-minute city has turned the neighbourhood ideal into measurable indicators. Reviews list dozens of measures that differ in the services they include, the travel thresholds they use and the way they combine services (Papadopoulos et al., 2023). Logan et al. (2022) defined the x-minute city as the time within which a resident can reach the nearest of every essential amenity, a definition that treats services as a bundle that is complete only when every element is present. Most measures are now computed at fine resolution, on hexagonal grids (Olivari et al., 2023) or cadastral parcels (Ferrer-Ortiz et al., 2022), and are reported as citywide shares, maps or inequality indices. They show that dense European cities already reach many services well within 15 minutes (Staricco, 2022), that within-city inequality remains large (Vale & Lopes, 2023) and that disadvantaged communities have lower access (Nicoletti et al., 2023). Proximity also matters for behaviour: differences in nearby amenities explain most of the variation in how much residents shop and visit locally (Abbiasov et al., 2024). The sufficiency perspective in transport justice gives the normative basis for such bundles. Every person should reach at least a minimum of each essential service (Lucas et al., 2016; Martens, 2016; Pereira et al., 2017), and sufficiency thresholds can be operationalised for whole cities (van der Veen et al., 2020), although most studies still set them without empirical justification (Jasso Chávez et al., 2026).

Facility location models provide the tools to close the gaps that such indicators reveal. The maximal covering location problem places a fixed number of facilities to maximise the population within a service distance (Church & ReVelle, 1974; Murray, 2016). A large literature adds equity objectives that favour the worst-off and measures the efficiency they cost (Marsh & Schilling, 1994; Karsu & Morton, 2015; Bertsimas et al., 2011). Aggregating demand to zones introduces measurement and coverage errors that fine grids avoid (Hillsman & Rhoda, 1978; Current & Schilling, 1990; Francis et al., 2009), which is one reason grid- and point-based models have become the norm.

Applied to the 15-minute city, these tools optimise over people. Bruno et al. (2024) redistributed services on 200 m hexagonal cells to equalise access per person across cities worldwide. Horton, Logan, et al. (2025) located grocery outlets in 500 US cities by minimising an inequality-adjusted mean distance over census blocks, with a scalable formulation for such equitable location problems (Horton, Murrell, et al., 2025). Xu et al. (2020) showed that relocating facilities could halve travel costs, and Chen et al. (2023) used a maximal covering model to raise the population within 15 minutes of primary care in Shenzhen. Huang and Khalil (2023) formulated walkability optimisation across several amenity types as an integer programme and applied it to low-walkability neighbourhoods in Toronto. Even models built for Chinese life circles impose their coverage targets on the study area as a whole (Zhai et al., 2023). An operations-research agenda for the 15-minute city notes that most of the literature has stayed with defining and measuring access (Arslan & Laporte, 2025).

Whether these solutions leave whole places unserved is rarely part of the objective. Location research has long recognised that maximising coverage favours dense areas and can leave sparse ones behind, as in emergency services for rural areas (Chanta et al., 2014). It has responded by adding equity as a second objective or as a side constraint (Mandell, 1991; Batta et al., 2014). Where zones enter 15-minute city optimisation, they enter as targets fixed from the outset. Jafari et al. (2023) set coverage targets for each destination type across several neighbourhoods of a hypothetical new town. Pemberton et al. (2026) added destinations in Melbourne until at least 80% of residents in each activity-centre catchment could reach every destination type within 10 minutes, and found that this improved access substantially but would be hard to implement in low-density suburbs. These studies assume that a zone-level target is wanted. They do not ask whether the same facilities placed on the grid would already fill the zones, or which unit the target should be set by.

### 2.3. Research gaps in assessing the necessity of living zones and this study's contributions

Although these literatures bear directly on living-zone planning, three gaps limit their use for deciding whether living zones are needed. First, 15-minute city studies mostly measure everyday amenities and report citywide shares, maps or inequality indices. They seldom diagnose, zone by zone, the bundle of public services that living-zone plans actually promise. Second, location studies for the 15-minute city optimise population coverage or distributional equity on fine grids or blocks. Where zones appear, they are imposed as targets rather than tested against grid rules. No study we found compares grid- and zone-based rules on the same facilities and counts the planning zones left without complete access to every service domain. Third, studies of living zones have asked how they should be delineated from mobility data (Ha et al., 2024; Park et al., 2026; Wu & Zhang, 2026) and how their boundaries affect the supply of local facilities (Park et al., 2023). They have not compared, under the same facility additions, which planning unit can actually carry a zone-level minimum standard.

To address these gaps, this study makes three contributions. (1) It measures bundle completion for the six public-service domains of Seoul's living-zone plan and diagnoses it zone by zone. (2) It places the same observed facility additions under grid-based rules, solved exactly, and under zone-based minimum standards, and shows that grid rules fill people but leave living zones empty. (3) It sets the same minimum standard by gu, living zone and dong, and tests whether official living-zone boundaries cut walkable access less than random partitions with the same number of zones. Together these tests give the necessity of living zones an empirical basis.


## 3. Data and methods

### 3.1. Study area: Seoul

Seoul covers 605 km² and had 9.34 million residents in 2024 (9.64 million in 2019), living on 30,785 populated 100 m grid cells. Its planning hierarchy is fully nested (Table 1, Fig. 1). The 25 gu are autonomous districts with their own elected councils and budgets (mean population 373,515). The 424 administrative dong are the smallest units of local administration (mean 22,023). Between them, the 2030 Seoul Living Zone Plan, adopted in March 2018, defines five regional living zones and 116 local living zones (Seoul Metropolitan Government, 2018). Each local living zone was drawn by grouping three to five dong with about 100,000 residents, taking into account topography, local centres and travel linkages between dong, without crossing gu boundaries; residents' panels of 30–40 members took part in planning each zone (Seoul Metropolitan Government, 2019). Today their populations average 80,499 (range 21,165–148,376). Each local living zone contains 3.7 dong on average (range 1–7), and each gu contains 4.6 local living zones (range 3–7). We refer to local living zones simply as living zones.

The plan is explicit about what a living zone is for. It lists eleven domains of daily public services, of which seven are to be supplied at the local living-zone level: parks, parking, libraries, senior leisure, youth and children's facilities, childcare and public sports. Their supply was diagnosed zone by zone with a 10-minute walking distance (Seoul Metropolitan Government, 2019, p. 86), and facilities are prioritised in living zones where residents request them, where none lies within a 10-minute or 800 m walk, and where provision falls below the Seoul average (Seoul Metropolitan Government, 2018). Seoul is thus a city that has already made the zone-level promise whose necessity we test.

Seoul is also one of the few cities where such a test can be carried out with public data. Residential population on a 100 m grid, facility registers with addresses for every public service type, an open street network, mobile-phone-based origin–destination flows between dong and the official living-zone boundaries are all publicly available for the same years. Comparable cities rarely release all of these at once, and in particular the fine-grained population and the official zone boundaries. We therefore use Seoul as a test case and leave replication in other cities to future work.

### 3.2. Data sources

**Population.** Residential population on the national 100 m grid for 2019 and 2024 from Statistics Korea's Statistical Geographic Information Service (SGIS), used for the 2020 and 2025 analyses respectively.

**Walking travel times.** Cell-to-cell walking times on the OpenStreetMap pedestrian network, using the January 2020 and January 2025 snapshots for Seoul and a 2 km buffer, at 4.0 km/h. Times are stored for all origin–destination pairs up to 30 minutes (22.1 and 22.6 million pairs).

**Facilities.** An inventory of 32 facility types for 31 December 2019 and 31 December 2024 (584,766 records), built from public licensing records (LOCALDATA, Ministry of the Interior and Safety), annual official registers and the Seoul Open Data Plaza. Records without source coordinates were geocoded only when the road address and building number, or the parcel number, matched exactly. Each record was assigned to its 100 m grid cell. Three layers needed for the plan's service domains were added. Public sports facilities come from the Ministry of Culture, Sports and Tourism's national inventory (387 and 456 facilities). Community child centres come from the Seoul Open Data Plaza (307 centres; current list, held fixed for both years). Parks come from the park layer of the 2030 Seoul Living Zone Plan (1,886 parks; 2018, held fixed). Because parks are areas, every grid cell that overlaps a park polygon is treated as a park destination.

**Service bundles.** We compare three bundles (Table 2). (a) Everyday functions: the seven categories of the accessibility inventory (education, culture, childcare and welfare, personal services, retail, health, and administration and safety). (b) The four amenities of Logan et al. (2022): pharmacy, supermarket, park and elementary school. (c) Planned public services: six of the seven local service domains of Seoul's plan—park, public library, senior leisure, youth and children, childcare and public sports. Parking is excluded because it serves cars rather than walking residents. Youth and children combines youth centres and community child centres. The six-domain bundle and its 10-minute threshold follow the plan's domains and its 10-minute walking criterion, but they are our operationalisation, not an official indicator.

**Boundaries.** Administrative dong (424; boundaries of July 2023), official living zones (116), gu (25) and, for comparison, 116 mobility communities. The mobility communities were derived from daytime non-commuting origin–destination flows between dong in the Seoul Living Mobility Dataset with the Leiden algorithm (Park et al., 2026). They represent zones drawn from where residents actually go.

### 3.3. Placement rules: grid-based versus zone-based

All experiments answer one question. If Seoul adds the facilities it actually added between 2020 and 2025, where should they go, and does the answer fill every living zone? We take the budget N for each facility type as its net increase in facility-occupied grid cells between the two years. For the bundle, the budgets are public library 31, senior facility 93, youth centre 11, public childcare centre 200 and public sports facility 46, or 381 in total; parks are not placed. For single facilities we also use cultural facilities (32), public kindergartens (54) and community centres (8). The budget is an upper bound on what was added, not a monetary budget. Candidate sites are populated or business-occupied cells without an existing facility of the same type. Every rule places exactly the same facilities; only the rule changes.

**Grid-based rules** treat the city as a surface of people and place facilities to optimise outcomes over people.

- *Grid efficiency* places each facility where it newly reaches the most residents.
- *Grid vulnerability-weighted* gives extra weight to residents in cells whose neighbourhood was poorly served before placement.
- For the bundle, *grid bundle maximisation* is the maximal covering location problem (Church & ReVelle, 1974) applied to the whole bundle. It chooses all 381 sites at once to maximise the number of residents who complete the bundle, and we solve it exactly as an integer programme (Appendix A, Eq. A.1).
- *Facility-by-facility* planning, which mirrors how separate departments plan their own facilities, solves an exact covering problem for each type on its own.
- A *coordinated* rule rewards cells for being closer to completion, with a weight that rises with the number of domains reached (Appendix A). It reaches the most deprived residents best and serves as the grid's equity rule for the bundle.

**Zone-based rules** treat the city as a set of places. They first meet a minimum standard in every unit of a chosen planning unit and then use the remaining facilities for efficiency. We apply the same rule to gu, official living zones and dong, so that only the planning unit changes. For single facilities, the minimum is a coverage share τ equal to 0.6 times the population-weighted median dong coverage of that facility. This follows the convention of setting deprivation lines at 60% of the median (Sun & Thakuriah, 2021). A hybrid rule meets the living-zone minimum first and places the rest with vulnerability weights. For the bundle, the minimum is that at least τ = 1% or 5% of a unit's residents complete the bundle. We add this as a constraint to the bundle maximisation, with a heavy penalty on any shortfall, so that minimums are met first (Appendix A, Eq. A.2). The minimum is capped at what is structurally attainable in each unit; in 2025 no living zone was below this cap. The two levels are deliberately low: 1% asks that at least some residents of every zone can walk to all six domains, and 5% roughly matches the citywide completion rate before placement.

### 3.4. Indices for evaluation and analytical procedure

#### 3.4.1. Evaluation indices

Every rule is scored on three report cards, one each for total access, for deprived people and for places. A rule that serves people well can still fail places, and the paper's question is whether only zone-based rules pass the third card.

- **Total access**: the share of residents who reach a facility within its threshold (single facilities) or complete the bundle (bundle completion rate). Completion follows the x-minute definition of Logan et al. (2022): a resident completes the bundle when the slowest of the nearest facilities of every domain is within the threshold.
- **Deprived people**: for single facilities, the share of the most vulnerable 20% of residents who are reached; for the bundle, completion among the bottom 20%, the residents who reached the fewest domains before placement (ties weighted fractionally).
- **Places**: the number of official living zones below the minimum standard (single facilities) and the number of zero-completion living zones, in which no resident completes the bundle.

Two further indices assess boundaries. **Boundary-restricted loss** is the decline in the share of residents reaching a facility when residents may use only facilities inside their own unit. **Boundary exposure** is the share of residents whose 15-minute walking catchment crosses a unit boundary.

#### 3.4.2. Analytical approach

The analysis follows the three research questions (Fig. 2). For RQ1, we compute completion curves from 0 to 20 minutes for the three bundles and map completion by living zone. For RQ2, we score every grid-based rule on the three report cards, for seven single facilities and for the bundle, in both years. For RQ3, we apply the zone-based rules to gu, official living zones and dong. For the bundle we add three random partitions of Seoul into 116 contiguous zones and the 116 mobility communities, to separate the effect of the living-zone scale from that of the official boundaries. To test whether the official boundaries themselves matter, we compare their boundary-restricted loss with that of random partitions that merge contiguous dong into the same number of zones as the plan within each gu, under three generators (population-balanced, dong-balanced and unconstrained; Appendix B). We repeat the test after randomly relocating facilities 20 times, so that the result cannot be an artefact of the observed facility pattern. Integer programmes were solved with HiGHS. The grid-based programmes reached proven optimality; the bundle minimum-standard programmes were solved within time limits (Appendix A).

## 4. Results

### 4.1. Data overview: service bundles in Seoul's living zones (RQ1)

Seoul's everyday functions are almost universally walkable (Table 3, Fig. 3). Within 15 minutes, 94.8% (2020) and 94.6% (2025) of residents reach all four amenities of Logan et al. (2022), and 73.1% and 77.3% reach all seven everyday categories. Five of the seven categories are within 15 minutes of more than 99% of residents. Among those who do not complete the everyday bundle, 86% and 84% lack only one category. By the standard of everyday functions, Seoul already is a 15-minute city.

The public services that the living-zone plan promises are a different matter. Only 3.7% (2020) and 5.3% (2025) of residents can reach all six domains within 10 minutes, and even at 15 minutes the shares rise only to 20.9% and 27.4%. The gap is not an artefact of the threshold: at the same 10 minutes, 37.2% and 39.9% complete the everyday bundle. Non-completion is also deep rather than marginal. Of the residents who do not complete the bundle, 83% (2020) and 80% (2025) lack two or more domains. Public sports (80%) and the public library (70%) are missing most often, whereas childcare is reached by 98% of residents.

What is missing is missing in places. In 50 (2020) and 38 (2025) of the 116 living zones, not a single resident completes the bundle, and in 91 and 73 zones fewer than 5% do (Fig. 5a). More than a third of Seoul's living zones offer no resident a 10-minute walk to all six services that the plan promises them. This is the gap a living-zone plan has to close.

### 4.2. Grid-based versus zone-based placement (RQ2)

#### 4.2.1. Single facilities

Grid-based placement does what it is designed to do (Table 4a, Fig. 4). Vulnerability-weighted placement reaches the most vulnerable residents better than the living-zone minimum in 12 of 14 facility–year combinations. For libraries in 2025, for example, it reaches 57.9% of vulnerable residents against 53.2% under the living-zone minimum, at an efficiency cost of about 0.1 percentage points. But it barely changes the number of living zones left below the minimum. For libraries, 11 zones remain below it under grid efficiency and 9 under vulnerability weighting (2020); for public kindergartens, 14 and 13. Across the seven facilities, grid placement leaves living zones below the minimum for six of them, the exception being senior facilities with 93 additions. The living-zone minimum brings that number to zero for six of the seven (Section 4.3.3). Vulnerability-weighted grid placement serves deprived residents best, yet it leaves nearly every under-served living zone under-served.

#### 4.2.2. Service bundle

The same holds, more starkly, for the bundle (Table 4b, Fig. 6). Solving the bundle maximisation exactly raises completion from 3.7% to 22.8% (2020) and from 5.3% to 24.2% (2025). This is 55% and 47% more than the exact facility-by-facility solution (14.7% and 16.5%), so planning the six domains together pays. Yet 18 (2020) and 14 (2025) living zones still have no resident completing the bundle (Fig. 5b). Facility-by-facility planning leaves 21 and 13. Weighting the objective towards deprived residents does not help places either: the coordinated rule reaches 5.8% and 6.3% of the bottom-20 group, the highest of all rules, but leaves 21 and 19 living zones at zero. Whether the grid is optimised for total completion or for the most deprived residents, 14 to 21 living zones remain in which no resident completes the bundle.

#### 4.2.3. People and places

The two goals pull in different directions, and the results show why. Completion needs every domain, and non-completers lack two or more domains in four cases out of five. A zone that lacks both a library and a sports facility gains no completion from one new library alone. The scarcest additions are the ones most often missing: 31 libraries and 46 sports facilities for 116 living zones. A person-based objective sends each of them to the cells where it completes the most residents, which are places that already have the other domains. The exact bundle maximisation therefore reaches only 0.1% and 0.2% of the bottom-20 group, because cells that lack many domains are rarely worth completing when the objective counts heads. The empty zones are not a failure of the optimiser; they are what a person-based objective produces.

For single facilities, the two goals can be reconciled. The hybrid rule, which meets the living-zone minimum first and places the rest with vulnerability weights, keeps every zone above the minimum and recovers vulnerable access. For public childcare it reaches 42.6% of vulnerable residents in both years, against 42.6% and 42.8% under vulnerability weighting; for public kindergartens, 35.4% and 36.8% against 35.3%. Filling people and filling places are different tasks. The first is done on the grid; the second requires a zone-level standard.

### 4.3. Planning units for minimum standards (RQ3)

#### 4.3.1. Gu

A standard set by gu changes almost nothing (Table 4, Fig. 6). For the bundle, zero-completion living zones remain at 18 (2020) and 12 (2025) under a 5% gu standard. The standard is binding: 16 (2020) and 14 (2025) gu fall below it before placement, and all of them meet it afterwards. Yet the cost in citywide completion is at most 0.05 percentage points, because a gu can meet its average without reaching the empty living zones inside it. For libraries, the gu standard leaves 10 and 7 living zones below the minimum, almost the same as grid efficiency. Aggregation to gu also hides more of the deficit than any other unit. Among under-served residents, the share living in units that meet the standard on average is 0.21 for dong, 0.34 for living zones and 0.43 for gu (libraries, 2020), and the order is the same for all ten facility types examined. A gu standard is met on paper while its living zones stay empty.

#### 4.3.2. Dong

A standard set by dong cannot be met. For libraries, meeting the dong standard in every dong requires 68 (2020) and 58 (2025) new libraries in the exact solution, against the 31 actually added. Living zones require 21 and 18, and gu 2. For the bundle, a 5% dong standard costs 4.6–5.2 percentage points of citywide completion and still leaves 198–221 of 424 dong below the standard. It does not reduce zero-completion living zones either (20 and 16). The same pattern appears across facilities. With random partitions of increasing number, we located for each facility the range of zone counts in which the observed additions can meet a minimum. The 116-zone scale lies inside that range for four facilities (library, cultural facility, public kindergarten and community centre), whereas the 424-dong scale lies outside it for six of seven. A dong standard spreads the additions too thinly to fill any place.

#### 4.3.3. Living zones

Only a standard set at the living-zone scale fills places. For single facilities, the living-zone minimum brings the number of living zones below the minimum to zero for six of seven facilities in both years. The exception, youth centres, has only 11 additions, and the number still falls from 21 to 7. For the bundle, a 5% living-zone minimum reduces zero-completion living zones from 18 to 3 (2020) and from 14 to 2 (2025), and zones below 5% from 33 to 9 and from 29 to 5 (Fig. 5c). The cost is 2.8 and 2.1 percentage points of citywide completion, and 1.3 and 0.6 points under a 1% minimum. Bottom-20 completion stays at 0.1–0.4%, about the same as under the grid maximisation.

The effect comes from the scale of the unit. Under the 5% standard, random 116-zone partitions reduce zero-completion living zones to 5–7 and the mobility communities to 4 (2025), whereas gu and dong do not reduce them at all. Because zero-completion is counted in official living zones, standards set on the same zones are favoured in this count. The scale result, not the ranking among 116-zone partitions, is the core finding. A minimum standard at the living-zone scale removes almost all empty living zones, from 14 to 2 in 2025, at a cost of about two percentage points of citywide completion.

#### 4.3.4. Official boundaries

Official living zones are not an arbitrary way to draw 116 zones. When residents may use only facilities inside their own zone, the share reaching a library falls by 10.0 percentage points with official boundaries but by 13.9 points (median) with random 116-zone partitions (2020). The difference holds for cultural facilities, kindergartens and childcare, in both years and under all three random generators (p ≤ 0.04). It also survives random relocation of facilities. In all 20 relocations of each of the seven facilities, official boundaries cut less access than the random median, so the result does not depend on where facilities happen to be today. The share of residents whose 15-minute walking catchment crosses a zone boundary is 0.84 for official living zones against 0.89 for random partitions, lower than every one of 40 draws. Finally, a minimum standard set on official living zones reduces shortfalls in the mobility communities, which were not used in placement, more than a standard set on random zones (six of seven facilities). Official living zones cut walkable access less than random partitions of the same number, consistent with their close alignment with residents' mobility communities (Park et al., 2026).

### 4.4. Robustness

The main results do not depend on the threshold, the budget or the facility layers. We report the variants already run for each part of the argument.

**Walking threshold and speed.** Extending the bundle threshold to 12 and 15 minutes raises completion before placement to 11.8% and 27.4% (2025). Planning the bundle together still beats facility-by-facility planning, by 28% at 12 minutes and 8% at 15 minutes in the exact solutions. For libraries, the order of the minimum number of additions needed to meet a standard in every unit holds in every variant: dong far above living zones, and living zones far above gu. This holds at 10 and 15 minutes, at 3.6 and 4.0 km/h and under four rules for τ. Dong need 45–105 additions against 31–32 available, living zones 9–49 and gu 1–17. Under the strictest rule, the citywide mean, even living zones exceed the budget (44–49), so the feasibility of the living-zone scale holds for practical rather than maximal standards.

**Budget.** In the greedy solutions, the coordination gain over facility-by-facility planning is +32% at the observed budget. Halving or doubling the budget changes its size (+34–35% at half; +17–25% at double) but not its direction.

**Facility layers.** The coordination gain persists when only public sports facilities with verified coordinates are used (+30–34%), when the 2024 urban-planning park layer replaces the 2018 layer (+33%) and when public sports are removed from the bundle (+9–10%). Removing community child centres from the youth and children domain halves completion under the coordinated rule (9.8% and 10.5%), which shows how much the bundle depends on that layer; the coordination gain rises to 56–68%.

**Transfer over time.** Sites chosen with 2020 data and evaluated on the 2025 population and network still complete the bundle for 18.0% of residents under the coordinated rule, against 13.1% for facility-by-facility sites.

**Solution quality.** All grid-based integer programmes reached proven optimality, and their solutions were re-evaluated independently with identical results. The bundle minimum-standard programmes were solved within time limits of 1.5 hours (gu, dong, random partitions and mobility communities) and 4 hours (official living zones). For official living zones the remaining optimality gaps were 3–49%. Longer runs improved the solutions: with 1.5 hours, 18 zero-completion living zones remained in 2020; with 4 hours, 3. The two or three zones that remain are therefore likely computational rather than structural. The gu programmes were solved to within 0.1% of optimality and still changed nothing, so the failure of the gu standard is not computational.

**Stability.** Under ±10% random perturbations of population, the sites chosen by each rule overlapped substantially (median Jaccard 0.64–1.0), with no systematic difference between grid and zone rules. Zone rules are not more stable than grid rules; their advantage lies in filling places.

## 5. Discussion and conclusion

### 5.1. Why grids leave places empty

This study asked why living zones are needed when accessibility can be measured and facilities located on grids. The first part of the answer is that the gap a living-zone plan must close is a gap in places. Seoul's everyday functions are within a short walk of almost everyone, but the public services its plan promises are not, and in more than a third of living zones no resident can walk to all six. The second part is that grids, however well optimised, do not close that gap. Placing the facilities Seoul actually added on the grid raises citywide completion four- to sixfold and, with vulnerability weights, reaches deprived residents better than any zone rule. Yet 14 to 21 living zones remain in which no resident completes the bundle.

The reason lies in the structure of the problem rather than in the optimiser. Completion requires every domain, and residents who lack the bundle usually lack two or more domains. A living zone that lacks a library and a sports facility gains nothing from one of them alone. A person-based objective, whether it counts all residents or weights the deprived, therefore sends scarce facilities to places that already have the other domains, where one addition completes many residents. The empty zones are what a person-based objective produces. Location research has long noted that maximal coverage favours dense areas over sparse ones (Chanta et al., 2014). Our results show that the same happens between living zones in a dense city, and that it persists when the objective is weighted towards deprived residents. They also extend the warning that average accessibility can mask inequality between people (Willberg et al., 2023; Mouratidis, 2024). Even person-based equity objectives can mask deficits between places, and they do so systematically when services must be used together.

### 5.2. Why living zones, and not gu or dong

The third part of the answer is that only the living-zone scale can carry a promise to every place. A minimum standard set by gu is met on paper while the living zones inside each gu stay empty; it costs almost nothing because it changes almost nothing. A minimum standard set by dong asks for more facilities than a city adds, so it spreads them too thinly to fill any place. The living-zone scale lies between these limits. It is small enough that a zone's average cannot hide an empty neighbourhood and large enough that the facilities actually added can meet a minimum in every zone. Random partitions with the same number of zones also reduce empty zones, so the scale itself does much of the work.

The official boundaries add to this. They cut walkable access less than random boundaries with the same number of zones, in both years, under three random generators and after random relocation of facilities. This is consistent with the way Seoul drew them, by grouping dong according to local centres and travel linkages (Seoul Metropolitan Government, 2019), and with their close alignment with the communities residents form through daily trips (Park et al., 2026). A living zone drawn around where people go is also a better container for the services they walk to.

These results give empirical content to arguments for intermediate planning units that have so far been largely normative. Territorial justice asks that every area receive a basic level of provision (Davies, 1968; Boyne & Powell, 1991). Fiscal equivalence asks that the unit of decision match the area of benefit (Olson, 1969). The debate on place-based policy asks when policy should target places rather than people (Barca et al., 2012). Our results show that these are not only normative positions: with the same facilities, a person-based rule and a place-based standard produce different cities. They also qualify a finding from mobility data that local variation in accessibility is not explained by administrative districts (Graells-Garrido et al., 2021). We find the same for the gu, whose standard leaves its empty living zones untouched, but not for the living-zone scale. If the goal is that every territory receives at least a minimum, the territory must be drawn at a scale where the minimum is both visible and attainable. Our results show where that scale lies in one city and why neither the larger nor the smaller unit can replace it.

### 5.3. Implications for living-zone and 15-minute city planning

For planning practice the results suggest a division of labour between grids and living zones. Accessibility should be measured, and candidate sites evaluated, on the grid, which is precise and serves people best. Promises and monitoring should be made by living zone, which is the unit at which a minimum for every place can be both seen and met. A living-zone plan can do this in three steps: state a minimum bundle standard for each living zone, meet it first with the facilities to be added, and allocate the remaining facilities by grid-based efficiency or vulnerability weights. The cost of the first step is modest, about two percentage points of citywide completion in Seoul. Reporting progress by gu would conceal the zones that remain empty, and setting standards by dong would promise what cannot be delivered.

These implications reach beyond Seoul. The 20-minute neighbourhoods of Melbourne, the x-minute neighbourhoods of Portland and Shanghai and China's national hierarchy of life circles all promise services to every neighbourhood (Rao et al., 2024; Ministry of Housing and Urban-Rural Development, 2018). They make the same kind of promise as Seoul's plan, and they face the same choice of unit. Most such programmes have not yet set measurable standards (Gower & Grodach, 2022). Where standards have been set by zone, as in Melbourne's activity-centre catchments, they improve access but are costly in low-density areas (Pemberton et al., 2026). Our results add that the scale of the zone decides whether a standard can work at all: too large and it is met without filling any empty place, too small and it cannot be met. Our test can be repeated wherever grid population, facility locations, a street network and the planning boundaries are available. Data of this kind are increasingly published, but rarely all at once and at this resolution, which is why we began with Seoul. Extending the test to other cities is the most direct next step.

### 5.4. Limitations and future research

Several limitations qualify these conclusions. First, the goal of a minimum in every living zone is taken from Seoul's plan. It is a normative premise: if only person-based equity matters, grids suffice, and our results do not then establish the necessity of living zones. Second, the bundle minimum-standard programmes were solved within time limits, with optimality gaps of 3–49%, and two or three living zones remained below the standard. Longer runs reduced them sharply, so the residual is likely computational, but we cannot prove that every zone can be filled. Third, for the bundle we did not test the hybrid rule that combines a living-zone standard with vulnerability weighting, which kept both people and places served for single facilities. Fourth, the budget is the observed increase in occupied cells rather than a cost-based budget, and land availability, facility size, capacity and age-specific demand are not modelled. Fifth, the six-domain bundle and the 10-minute threshold are our operationalisation of the plan; the park and community child centre layers are held fixed, and public sports facilities have coordinates of moderate accuracy. Finally, the analysis covers one city at two points in time and does not identify causal effects of past plans. Future research should repeat the test in other cities with different planning units, add capacity and cost to the placement models, and examine whether living-zone standards change how residents actually use local services.

### 5.5. Conclusion

Grids fill people, not places. Planning daily services on a fine grid serves residents efficiently and can favour the deprived, but it leaves whole living zones without the services a living-zone plan promises. Only a minimum standard set at the living-zone scale fills those places, at a small cost to citywide access; standards set by larger districts hide the gaps, and standards set by smaller neighbourhoods cannot be met. Living zones are therefore necessary for any plan that promises daily public services to every place, and neither grids nor the administrative units above and below them can substitute for them.

## Appendix A. Integer programmes

**Bundle maximisation (grid).** Let *i* index populated cells with population *p_i*, *s* the five placed facility types, *j* candidate sites, and *K_i* the domains already reached from *i* before placement. *A^s_ij* = 1 if a facility of type *s* at *j* lies within the threshold of *i*. With binary siting variables *x_sj* and completion variables *z_i* ∈ [0, 1]:

max Σ_i p_i z_i, subject to z_i ≤ Σ_j A^s_ij x_sj for all i and all s ∉ K_i; Σ_j x_sj ≤ N_s for all s; x_sj ∈ {0, 1}.   (A.1)

Cells that miss the park domain cannot complete and are fixed at *z_i* = 0. The facility-by-facility benchmark solves, for each *s* separately, max Σ_i p_i y_i subject to y_i ≤ Σ_j A^s_ij x_sj and Σ_j x_sj ≤ N_s.

**Bundle minimum standard (zone).** For a partition into units *u* with population *pop_u* and pre-placement completers *base_u*, add to (A.1)

Σ_{i∈u} p_i z_i + pop_u · d_u ≥ τ_u · pop_u − base_u for all u, with d_u ≥ 0,   (A.2)

and replace the objective by Σ_i p_i z_i − M Σ_u pop_u d_u with *M* = 50, so that shortfalls are removed before total completion is maximised. τ_u = min(τ, τ̄_u), where τ̄_u is the share of residents of *u* in cells that can complete the bundle.

**Coordinated rule.** Facilities are added one at a time to maximise Σ_i p_i (c_i/6)^P, where *c_i* is the number of domains reached from cell *i*. The marginal gain of every affected candidate is recomputed after each placement, so the greedy step is exact. We report *P* = 2, which favours the most deprived, with *P* = 4 and *P* = 8 as sensitivity cases.

**Solver settings.** HiGHS via SciPy. Grid programmes: proven optimal (gap 0) in 0.3–1.4 hours. Zone programmes: time limits of 1.5 hours (gu, dong, random partitions, mobility communities) and 4 hours (official living zones). Table A.1 reports the gaps.

## Appendix B. Random partitions and facility relocation

Random partitions keep the number of living zones that the plan assigns to each gu and merge contiguous dong within each gu into that many zones, so that they differ from the official zones only in where the boundaries run. Three generators were used: population-balanced, dong-balanced and unconstrained region growing. For the boundary-restricted loss we drew 150 population-balanced partitions per year, and for the significance test 100 partitions under each generator. The p-value is the share of random partitions whose loss is no greater than that of the official living zones. For relocation, the facilities of each type were redrawn 20 times at random among their candidate and existing cells, keeping their number, and losses were recomputed for the official boundaries and for the median of ten random partitions. Boundary exposure was compared with 40 random partitions.

## References

Abbiasov, T., Heine, C., Sabouri, S., Salazar-Miranda, A., Santi, P., Glaeser, E., & Ratti, C. (2024). The 15-minute city quantified using human mobility data. *Nature Human Behaviour*, *8*(3), 445–455. https://doi.org/10.1038/s41562-023-01770-y

Allam, Z., Nieuwenhuijsen, M., Chabaud, D., & Moreno, C. (2022). The 15-minute city offers a new framework for sustainability, liveability, and health. *The Lancet Planetary Health*, *6*(3), e181–e183. https://doi.org/10.1016/S2542-5196(22)00014-6

Arslan, O., & Laporte, G. (2025). The 15-minute city concept: An operations research perspective and a research agenda. *Transportation Research Part E: Logistics and Transportation Review*, *202*, 104287. https://doi.org/10.1016/j.tre.2025.104287

Barca, F., McCann, P., & Rodríguez-Pose, A. (2012). The case for regional development intervention: Place-based versus place-neutral approaches. *Journal of Regional Science*, *52*(1), 134–152. https://doi.org/10.1111/j.1467-9787.2011.00756.x

Batta, R., Lejeune, M., & Prasad, S. (2014). Public facility location using dispersion, population, and equity criteria. *European Journal of Operational Research*, *234*(3), 819–829. https://doi.org/10.1016/j.ejor.2013.10.032

Bertsimas, D., Farias, V. F., & Trichakis, N. (2011). The Price of Fairness. *Operations Research*, *59*(1), 17–31. https://doi.org/10.1287/opre.1100.0865

Boyne, G., & Powell, M. (1991). Territorial justice: A review of theory and evidence. *Political Geography Quarterly*, *10*(3), 263–281. https://doi.org/10.1016/0260-9827(91)90038-V

Bruno, M., Monteiro Melo, H. P., Campanelli, B., & Loreto, V. (2024). A universal framework for inclusive 15-minute cities. *Nature Cities*, *1*(10), 633–641. https://doi.org/10.1038/s44284-024-00119-4

Chanta, S., Mayorga, M. E., & McLay, L. A. (2014). Improving emergency service in rural areas: a bi-objective covering location model for EMS systems. *Annals of Operations Research*, *221*(1), 133–159. https://doi.org/10.1007/s10479-011-0972-6

Chau, H.-W., Gilzean, I., Jamei, E., Palmer, L., Preece, T., & Quirke, M. (2022). Comparative Analysis of 20-Minute Neighbourhood Policies and Practices in Melbourne and Scotland. *Urban Planning*, *7*(4). https://doi.org/10.17645/up.v7i4.5668

Chen, L., Zeng, H., Wu, L., Tian, Q., Zhang, N., He, R., Xue, H., Zheng, J., Liu, J., Liang, F., & Zhu, B. (2023). Spatial Accessibility Evaluation and Location Optimization of Primary Healthcare in China: A Case Study of Shenzhen. *GeoHealth*, *7*(5), Article e2022GH000753. https://doi.org/10.1029/2022GH000753

Church, R., & ReVelle, C. (1974). The maximal covering location problem. *Papers of the Regional Science Association*, *32*(1), 101–118. https://doi.org/10.1007/BF01942293

Cranshaw, J., Schwartz, R., Hong, J., & Sadeh, N. (2012). The Livehoods Project: Utilizing Social Media to Understand the Dynamics of a City. *Proceedings of the International AAAI Conference on Web and Social Media*, *6*(1), 58–65. https://doi.org/10.1609/icwsm.v6i1.14278

Current, J. R., & Schilling, D. A. (1990). Analysis of Errors Due to Demand Data Aggregation in the Set Covering and Maximal Covering Location Problems. *Geographical Analysis*, *22*(2), 116–126. https://doi.org/10.1111/j.1538-4632.1990.tb00199.x

Davies, B. (1968). *Social needs and resources in local services: A study of variations in standards of provision of personal social services between local authority areas*. Michael Joseph.

Ferrer-Ortiz, C., Marquet, O., Mojica, L., & Vich, G. (2022). Barcelona under the 15-Minute City Lens: Mapping the Accessibility and Proximity Potential Based on Pedestrian Travel Times. *Smart Cities*, *5*(1), 146–161. https://doi.org/10.3390/smartcities5010010

Fotheringham, A. S., & Wong, D. W. S. (1991). The Modifiable Areal Unit Problem in Multivariate Statistical Analysis. *Environment and Planning A: Economy and Space*, *23*(7), 1025–1044. https://doi.org/10.1068/a231025

Francis, R. L., Lowe, T. J., Rayco, M. B., & Tamir, A. (2009). Aggregation error for location models: survey and analysis. *Annals of Operations Research*, *167*(1), 171–208. https://doi.org/10.1007/s10479-008-0344-z

Gao, F., Kihal, W., Le Meur, N., Souris, M., & Deguen, S. (2017). Does the edge effect impact on the measure of spatial accessibility to healthcare providers? *International Journal of Health Geographics*, *16*(1), Article 46. https://doi.org/10.1186/s12942-017-0119-3

Gower, A., & Grodach, C. (2022). Planning Innovation or City Branding? Exploring How Cities Operationalise the 20-Minute Neighbourhood Concept. *Urban Policy and Research*, *40*(1), 36–52. https://doi.org/10.1080/08111146.2021.2019701

Graells-Garrido, E., Serra-Burriel, F., Rowe, F., Cucchietti, F. M., & Reyes, P. (2021). A city of cities: Measuring how 15-minutes urban accessibility shapes human mobility in Barcelona. *PLOS ONE*, *16*(5), e0250080. https://doi.org/10.1371/journal.pone.0250080

Ha, J., & Lee, S. (2016). A Study on the Designation of Living Zones by Its Spatial Hierarchy Using OD Data and Community Detection Technique : Focused on the 2010 Household Travel Survey Data of the Seoul Metropolitan Area. *Journal of Korea Planning Association*, *51*(6), 79–98. https://doi.org/10.17208/jkpa.2016.11.51.6.79

Ha, J., Kim, Y., & Lee, S. (2024). Analysis of Functional Living Zones Changes and Influencing Factors of Travel Distance Before and After COVID-19 in Seoul, Korea : Using Mobile Phone-based Mobility Bigdata and Community Detection. *Journal of Korea Planning Association*, *59*(2), 73–92. https://doi.org/10.17208/jkpa.2024.04.59.2.73

Hastings, A. (2007). Territorial Justice and Neighbourhood Environmental Services: A Comparison of Provision to Deprived and Better-off Neighbourhoods in the UK. *Environment and Planning C: Government and Policy*, *25*(6), 896–917. https://doi.org/10.1068/c0657

Hewko, J., Smoyer-Tomic, K. E., & Hodgson, M. J. (2002). Measuring Neighbourhood Spatial Accessibility to Urban Amenities: Does Aggregation Error Matter? *Environment and Planning A: Economy and Space*, *34*(7), 1185–1206. https://doi.org/10.1068/a34171

Hillsman, E. L., & Rhoda, R. (1978). Errors in measuring distances from populations to service centers. *The Annals of Regional Science*, *12*(3), 74–88. https://doi.org/10.1007/BF01286124

Hipp, J. R., & Boessen, A. (2013). Egohoods as waves washing across the city: A new measure of "neighborhoods". *Criminology*, *51*(2), 287–327. https://doi.org/10.1111/1745-9125.12006

Hooghe, L., & Marks, G. (2003). Unraveling the central state, but how? Types of multi-level governance. *American Political Science Review*, *97*(2), 233–243. https://doi.org/10.1017/S0003055403000649

Horton, D., Logan, T. M., Speakman, E., & Skipper, D. (2025). Hundreds of grocery outlets needed across the United States to achieve walkable cities. *Nature Communications*, *16*(1), Article 6051. https://doi.org/10.1038/s41467-025-61454-1

Horton, D., Murrell, J., Skipper, D., Speakman, E., & Logan, T. (2025). A scalable optimization approach for equitable facility location: Methodology and transportation applications. *Transportation Research Part B: Methodological*, *201*, 103319. https://doi.org/10.1016/j.trb.2025.103319

Huang, W., & Khalil, E. B. (2023). Walkability Optimization: Formulations, Algorithms, and a Case Study of Toronto. *Proceedings of the AAAI Conference on Artificial Intelligence*, *37*(12), 14249–14258. https://doi.org/10.1609/aaai.v37i12.26667

Jafari, A., Singh, D., & Giles-Corti, B. (2023). Residential density and 20-minute neighbourhoods: A multi-neighbourhood destination location optimisation approach. *Health & Place*, *83*, 103070. https://doi.org/10.1016/j.healthplace.2023.103070

Jasso Chávez, J. A., Kelly, N., Pereira, R. H. M., Boisjoly, G., & Manaugh, K. (2026). Revisiting sufficientarianism in accessibility research: a review of accessibility poverty. *Transport Reviews*. Advance online publication, 1–29. https://doi.org/10.1080/01441647.2026.2720413

Jiao, H., & Xiao, M. (2022). Delineating Urban Community Life Circles for Large Chinese Cities Based on Mobile Phone Data and POI Data—The Case of Wuhan. *ISPRS International Journal of Geo-Information*, *11*(11), 548. https://doi.org/10.3390/ijgi11110548

Karsu, Ö., & Morton, A. (2015). Inequity averse optimization in operational research. *European Journal of Operational Research*, *245*(2), 343–359. https://doi.org/10.1016/j.ejor.2015.02.035

Khavarian-Garmsir, A. R., Sharifi, A., Hajian Hossein Abadi, M., & Moradi, Z. (2023). From Garden City to 15-Minute City: A Historical Perspective and Critical Assessment. *Land*, *12*(2), 512. https://doi.org/10.3390/land12020512

Kim, Y., Oh, J., & Kim, S. (2020). The Transition from Traditional Infrastructure to Living SOC and Its Effectiveness for Community Sustainability: The Case of South Korea. *Sustainability*, *12*(24), 10227. https://doi.org/10.3390/su122410227

Kline, P., & Moretti, E. (2014). People, Places, and Public Policy: Some Simple Welfare Economics of Local Economic Development Programs. *Annual Review of Economics*, *6*(1), 629–662. https://doi.org/10.1146/annurev-economics-080213-041024

Kwan, M.-P. (2012). The Uncertain Geographic Context Problem. *Annals of the Association of American Geographers*, *102*(5), 958–968. https://doi.org/10.1080/00045608.2012.687349

Lawhon, L. L. (2009). The neighborhood unit: Physical design or physical determinism? *Journal of Planning History*, *8*(2), 111–132. https://doi.org/10.1177/1538513208327072

Liu, T., & Chai, Y. (2015). Daily life circle reconstruction: A scheme for sustainable development in urban China. *Habitat International*, *50*, 250–260. https://doi.org/10.1016/j.habitatint.2015.08.038

Logan, T., Hobbs, M., Conrow, L., Reid, N., Young, R., & Anderson, M. (2022). The x-minute city: Measuring the 10, 15, 20-minute city and an evaluation of its use for sustainable urban design. *Cities*, *131*, 103924. https://doi.org/10.1016/j.cities.2022.103924

Lucas, K., van Wee, B., & Maat, K. (2016). A method to evaluate equitable accessibility: combining ethical theories and accessibility-based approaches. *Transportation*, *43*(3), 473–490. https://doi.org/10.1007/s11116-015-9585-2

Ma, W., Wang, N., Li, Y., & Sun, D. (2023). 15-min pedestrian distance life circle and sustainable community governance in Chinese metropolitan cities: A diagnosis. *Humanities and Social Sciences Communications*, *10*(1), Article 364. https://doi.org/10.1057/s41599-023-01812-w

Mandell, M. B. (1991). Modelling Effectiveness-Equity Trade-Offs in Public Service Delivery Systems. *Management Science*, *37*(4), 467–482. https://doi.org/10.1287/mnsc.37.4.467

Marchigiani, E., & Bonfantini, B. (2022). Urban Transition and the Return of Neighbourhood Planning. Questioning the Proximity Syndrome and the 15-Minute City. *Sustainability*, *14*(9), 5468. https://doi.org/10.3390/su14095468

Marsh, M. T., & Schilling, D. A. (1994). Equity measurement in facility location analysis: A review and framework. *European Journal of Operational Research*, *74*(1), 1–17. https://doi.org/10.1016/0377-2217(94)90200-3

Martens, K. (2016). *Transport justice: Designing fair transportation systems*. Routledge. https://doi.org/10.4324/9781315746852

Ministry of Housing and Urban-Rural Development. (2018). *Standard for urban residential area planning and design* (GB 50180-2018) [in Chinese]. Announcement No. 142, 10 July 2018. http://www.moe.gov.cn/jyb_xwfb/xw_zt/moe_357/jyzt_2019n/2019_zt13/zcwj/201906/t20190606_384732.html

Moreno, C., Allam, Z., Chabaud, D., Gall, C., & Pratlong, F. (2021). Introducing the “15-Minute City”: Sustainability, Resilience and Place Identity in Future Post-Pandemic Cities. *Smart Cities*, *4*(1), 93–111. https://doi.org/10.3390/smartcities4010006

Mouratidis, K. (2024). Time to challenge the 15-minute city: Seven pitfalls for sustainability, equity, livability, and spatial analysis. *Cities*, *153*, 105274. https://doi.org/10.1016/j.cities.2024.105274

Murray, A. T. (2016). Maximal Coverage Location Problem: Impacts, Significance, and Evolution. *International Regional Science Review*, *39*(1), 5–27. https://doi.org/10.1177/0160017615600222

Nicoletti, L., Sirenko, M., & Verma, T. (2023). Disadvantaged communities have lower access to urban infrastructure. *Environment and Planning B: Urban Analytics and City Science*, *50*(3), 831–849. https://doi.org/10.1177/23998083221131044

Office for Government Policy Coordination. (2019, April 15). *Gyms and libraries within 10 minutes anywhere: KRW 30 trillion for Life SOC* [in Korean]. Korea Policy Briefing. https://www.korea.kr/news/policyNewsView.do?newsId=148860006

Olivari, B., Cipriano, P., Napolitano, M., & Giovannini, L. (2023). Are Italian cities already 15-minute? Presenting the Next Proximity Index: A novel and scalable way to measure it, based on open data. *Journal of Urban Mobility*, *4*, 100057. https://doi.org/10.1016/j.urbmob.2023.100057

Olson, M. (1969). The principle of "fiscal equivalence": The division of responsibilities among different levels of government. *American Economic Review*, *59*(2), 479–487. https://www.jstor.org/stable/1823700

Openshaw, S. (1984). *The modifiable areal unit problem* (Concepts and Techniques in Modern Geography No. 38). Geo Books.

Papadopoulos, E., Sdoukopoulos, A., & Politis, I. (2023). Measuring compliance with the 15-minute city concept: State-of-the-art, major components and further requirements. *Sustainable Cities and Society*, *99*, 104875. https://doi.org/10.1016/j.scs.2023.104875

Park, J., Eom, S., & Lee, M.-H. (2026). Benchmarking living-zone plans with mobility community detection: Evidence from Seoul's mobile-phone-based mobility data. *Journal of Transport Geography*, *135*, 104753. https://doi.org/10.1016/j.jtrangeo.2026.104753

Park, J., Lee, J. W., & Lee, H. C. (2023). A Study on the Accessibility and Edge Effect in Life-SOC(Social Overhead Capital) Allocation - A Case Study of 『Seoul Plan 2030』 Living-Area(Neighborhood) Planning. *Journal of the Urban Design Institute of Korea Urban Design*, *24*(3), 137–155. https://doi.org/10.38195/judik.2023.06.24.3.137

Park, Y., & Rogers, G. O. (2015). Neighborhood Planning Theory, Guidelines, and Research: Can Area, Population, and Boundary Guide Conceptual Framing? *Journal of Planning Literature*, *30*(1), 18–36. https://doi.org/10.1177/0885412214549422

Pemberton, S., Saghapour, T., Giles-Corti, B., Abdollahyar, M., Both, A., Pearson, D., Higgs, C., Jafari, A., Singh, D., Gunn, L., Woodcock, J., & Zapata-Diomedi, B. (2026). Infrastructure and accessibility implications of implementing x-minute city policies in low-density contexts. *Cities*, *171*, 106717. https://doi.org/10.1016/j.cities.2025.106717

Pereira, R. H. M., Schwanen, T., & Banister, D. (2017). Distributive justice and equity in transportation. *Transport Reviews*, *37*(2), 170–191. https://doi.org/10.1080/01441647.2016.1257660

Perry, C. A. (1929). The neighborhood unit. In *Neighborhood and community planning* (Regional Survey of New York and Its Environs, Vol. 7, Monograph 1). Regional Plan of New York and Its Environs.

Qi, L., Harumain, Y. A. S., & Dali, M. M. (2025). Enhancing Sustainability: A Systematic Review of the Livable Neighborhood Life Circle and Its Prospects in China. *Sustainability*, *17*(19), 8813. https://doi.org/10.3390/su17198813

Rao, F., Kong, Y., Ng, K. H., Xie, Q., & Zhu, Y. (2024). Unravelling the Spatial Arrangement of the 15-Minute City: A Comparative Study of Shanghai, Melbourne, and Portland. *Planning Theory & Practice*, *25*(2), 184–206. https://doi.org/10.1080/14649357.2024.2350948

Ratti, C., Sobolevsky, S., Calabrese, F., Andris, C., Reades, J., Martino, M., Claxton, R., & Strogatz, S. H. (2010). Redrawing the Map of Great Britain from a Network of Human Interactions. *PLoS ONE*, *5*(12), e14248. https://doi.org/10.1371/journal.pone.0014248

Seoul Metropolitan Government. (2018, March 7). *Our neighbourhood's future: Living zone plans for 116 areas announced* [in Korean]. Seoul Information Communication Plaza. https://opengov.seoul.go.kr/mediahub/14781653

Seoul Metropolitan Government. (2019). *2030 Seoul living zone plan white paper* [in Korean]. Seoul Metropolitan Government. ISBN 979-11-6161-147-1

Sharifi, A. (2016). From Garden City to Eco-urbanism: The quest for sustainable neighborhood development. *Sustainable Cities and Society*, *20*, 1–16. https://doi.org/10.1016/j.scs.2015.09.002

Shin, J., Newman, G. D., & Park, Y. (2024). Urban versus rural disparities in amenity proximity and housing price: the case of integrated urban–rural city, Sejong, South Korea. *Journal of Housing and the Built Environment*, *39*(2), 727–747. https://doi.org/10.1007/s10901-023-10098-y

Staricco, L. (2022). 15-, 10- or 5-minute city? A focus on accessibility to services in Turin, Italy. *Journal of Urban Mobility*, *2*, 100030. https://doi.org/10.1016/j.urbmob.2022.100030

Stępniak, M., & Jacobs-Crisioni, C. (2017). Reducing the uncertainty induced by spatial aggregation in accessibility and spatial interaction applications. *Journal of Transport Geography*, *61*, 17–29. https://doi.org/10.1016/j.jtrangeo.2017.04.001

Sun, Y., & Thakuriah, P. (2021). Public transport availability inequalities and transport poverty risk across England. *Environment and Planning B: Urban Analytics and City Science*, *48*(9), 2775–2789. https://doi.org/10.1177/2399808321991536

Tao, Z., Cheng, Y., Zheng, Q., & Li, G. (2018). Measuring spatial accessibility to healthcare services with constraint of administrative boundary: a case study of Yanqing District, Beijing, China. *International Journal for Equity in Health*, *17*(1), Article 7. https://doi.org/10.1186/s12939-018-0720-5

Vale, D., & Lopes, A. S. (2023). Accessibility inequality across Europe: a comparison of 15-minute pedestrian accessibility in cities with 100,000 or more inhabitants. *npj Urban Sustainability*, *3*(1), Article 55. https://doi.org/10.1038/s42949-023-00133-w

van der Veen, A. S., Annema, J. A., Martens, K., van Arem, B., & Correia, G. H. d. A. (2020). Operationalizing an indicator of sufficient accessibility – a case study for the city of Rotterdam. *Case Studies on Transport Policy*, *8*(4), 1360–1370. https://doi.org/10.1016/j.cstp.2020.09.007

Ville de Paris. (n.d.). *Paris ville du quart d'heure, ou le pari de la proximité*. Retrieved October 1, 2026, from https://www.paris.fr/dossiers/paris-ville-du-quart-d-heure-ou-le-pari-de-la-proximite-37

Weng, M., Ding, N., Li, J., Jin, X., Xiao, H., He, Z., & Su, S. (2019). The 15-minute walkable neighborhoods: Measurement, social inequalities and implications for building healthy communities in urban China. *Journal of Transport & Health*, *13*, 259–273. https://doi.org/10.1016/j.jth.2019.05.005

Willberg, E., Fink, C., & Toivonen, T. (2023). The 15-minute city for all? – Measuring individual and temporal variations in walking accessibility. *Journal of Transport Geography*, *106*, 103521. https://doi.org/10.1016/j.jtrangeo.2022.103521

Wu, H., Wang, L., Zhang, Z., & Gao, J. (2021). Analysis and optimization of 15-minute community life circle based on supply and demand matching: A case study of Shanghai. *PLOS ONE*, *16*(8), e0256904. https://doi.org/10.1371/journal.pone.0256904

Wu, Y., & Zhang, W. (2026). Is a Life Circle a Circle? Topological Data Analysis on Activity Space Delineation. *Annals of the American Association of Geographers*, *116*(7), 1600–1624. https://doi.org/10.1080/24694452.2025.2608173

Xu, Y., Olmos, L. E., Abbar, S., & González, M. C. (2020). Deconstructing laws of accessibility and facility distribution in cities. *Science Advances*, *6*(37), Article eabb4112. https://doi.org/10.1126/sciadv.abb4112

Yang, C., & Qian, Z. (2024). The new paradigm of future cities? Facilitating dialogues between the 15-minute city and the 15-minute life circle in China based on a bibliometric analysis. *Transactions in Planning and Urban Research*, *3*(3), 294–312. https://doi.org/10.1177/27541223241274491

Zhai, S., Kong, Y., Song, G., & Luo, J. (2023). A new facility location problem for urban public facility planning toward 15-minute life circle: Model and experiment [in Chinese]. *Acta Geographica Sinica*, *78*(6), 1484–1497. https://doi.org/10.11821/dlxb202306010

## Figure captions

**Fig. 1.** Study area: Seoul's 25 gu, 116 official living zones and 424 administrative dong.

**Fig. 2.** Analytical framework. The same facility additions (net increase 2020–2025) are placed under grid-based and zone-based rules and scored on three report cards.

**Fig. 3.** Bundle completion. (a, b) Share of residents completing each bundle by walking time, 2020 and 2025; dotted lines mark 10 and 15 minutes. (c) Number of missing domains among residents who do not complete the bundle, 2025.

**Fig. 4.** Official living zones below the minimum standard after placing the observed additions of each facility, by placement rule. (a) 2020, (b) 2025.

**Fig. 5.** Share of residents completing the six-domain bundle within 10 minutes, by official living zone, 2025. (a) Before placement; (b) after grid bundle maximisation (exact maximal covering); (c) after placement under a 5% living-zone minimum standard.

**Fig. 6.** Zero-completion official living zones after placing the 381 additions under each rule, (a) 2020 and (b) 2025. Random and mobility-community partitions were run for 2025 only.

## Tables

- Table 1. Planning hierarchy of Seoul.
- Table 2. Planned public-service bundle: domains, facility cells and placement budget.
- Table 3. Bundle completion rate by walking-time threshold.
- Table 4. Three report cards by placement rule: (a) single facilities, (b) six-domain bundle.
