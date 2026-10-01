# Grids fill people, not places: Testing the necessity of living zones for walkable public services in Seoul

*Draft v1 (2026-10-02). Structure follows Park, Eom & Lee (2026, Journal of Transport Geography). Numbers are taken from `results/` tables; see `연구설계.md` (4th edition) for the evidence register.*

## Abstract

Planning self-contained neighbourhoods has become a central strategy for walkable cities, and Seoul's 2030 Living Zone Plan commits to providing a common set of daily public services in each of its 116 official living zones. Yet walking accessibility can now be measured and optimised on fine grids, which raises a basic question: why plan through intermediate living zones at all? This study tests the necessity of living zones by asking whether grid-based facility planning can fill every zone, and at which planning unit a zone-level minimum standard can be guaranteed. Using a 100 m population grid, walking travel times on the OpenStreetMap network and facility inventories for 2020 and 2025, we define bundle completion as walking access to all six service domains of the plan within 10 minutes, and we simulate the facilities actually added over five years under grid-based and zone-based placement rules, including exact integer programmes. Only 3.7–5.3% of residents complete the bundle, and in 38–50 living zones no resident does. Grid-based placement fills people but not places: maximising total completion raises it by 47–55% over facility-by-facility planning, and vulnerability-weighted placement best reaches deprived residents, yet both leave 14–21 living zones with zero completion. Only a living-zone minimum standard removes or nearly removes such zones (from 14 to 2 for the bundle; to zero for six of seven single facilities) at a cost of 0–3 percentage points of citywide access. The same standard set by gu changes nothing, and set by dong it cannot be met with the facilities available. Official living-zone boundaries also cut walkable access less than random 116-zone partitions. Living zones are therefore necessary for the plan's zone-level service goal, and neither grids, gu nor dong can substitute for them.

**Highlights**
- Only 3.7–5.3% of Seoul residents reach all six planned services within 10 min
- Grid-based placement fills people but leaves 14–21 living zones without access
- Only living-zone minimum standards eliminate zones without complete access
- Gu-level standards change nothing; dong-level standards are infeasible
- Official living zones cut walkable access less than random 116-zone partitions

**Keywords:** Living zone plan; Walking accessibility; Minimum service standard; Facility location; Planning unit; Seoul

---

## 1. Introduction

Planning walkable, self-contained neighbourhoods has returned to the centre of urban policy. The most visible expression is the 15-minute city, which asks that the services residents need every day—shops, schools, health care, parks, culture—lie within a short walk or cycle of home (Moreno et al., 2021; Allam et al., 2022). The idea has spread quickly from Paris to cities on every continent, and a growing literature measures how far real cities fall short of it (Logan et al., 2022; Papadopoulos et al., 2023; Willberg et al., 2023; Abbiasov et al., 2024). Practices nonetheless differ widely, and many cities that adopt the label are still at an early, planning-only stage (Teixeira et al., 2024).

Behind these ideas sits an older planning device. Since Perry's (1929) neighbourhood unit, which sized a residential area by the walking catchment of an elementary school and equipped it with shops, parks and community facilities, planners have organised daily services within territories that are smaller than a city and larger than a block (Park and Rogers, 2015). We call these territories living zones. Many cities keep such intermediate planning units today. Berlin divides its twelve boroughs into more than 500 Lebensweltlich orientierte Räume that structure social monitoring and budgeting (Berlin Senate Department for Urban Development, Building and Housing, 2021). Seoul's 2030 Living Zone Plan divides the city into five large and 116 local living zones and commits to supplying a common set of daily public services—parks, libraries, senior leisure, youth and children's facilities, childcare, public sports and parking—in each local living zone (Seoul Metropolitan Government, 2018). Korea's national Life SOC programme promises daily facilities "within ten minutes" of home (Office for Government Policy Coordination, 2019).

Yet the tools that motivated the 15-minute city have also made the living zone look redundant. Walking accessibility can now be computed cell by cell on 100 m grids, and facilities can be located on the same grid by optimisation models that maximise coverage or equity (Church and ReVelle, 1974; Marsh and Schilling, 1994; Talen and Anselin, 1998). If the grid can both diagnose and fix, why plan through an intermediate unit at all? Previous studies of Seoul asked whether the official living-zone boundaries match the communities that residents actually form through their daily trips (Park et al., 2025; Park et al., 2026). They did not ask whether the living zone itself is necessary.

This paper argues that the answer depends on what a living-zone plan promises. Seoul's plan does not only promise that more people will reach services; it promises that every living zone will be supplied. That is a promise about places, not only about people (Boyne and Powell, 1991). Living zones are necessary if, and only if, planning on the grid fails to fill every zone while a standard set at the living-zone scale succeeds—and neither the larger gu nor the smaller administrative dong can do the same job. We test this proposition directly.

Using a 100 m population grid, walking travel times on the OpenStreetMap network and facility inventories for 2020 and 2025, we measure whether residents can reach all six public-service domains of Seoul's plan within a 10-minute walk, and we simulate the facilities that Seoul actually added between 2020 and 2025 under grid-based and zone-based placement rules, including exact integer programmes. Three research questions (RQs) structure the analysis:

- **RQ1**: How completely do Seoul's living zones provide the bundle of daily public services promised by the living-zone plan, compared with everyday commercial functions?
- **RQ2**: Can grid-based facility placement, whether maximising total access or prioritising deprived residents, fill every living zone?
- **RQ3**: At which planning unit—gu, living zone or dong—can a zone-level minimum standard be met with the facilities actually added, and do official living-zone boundaries matter?

By answering these questions, the paper makes three contributions. First, it measures bundle completion for the services that living-zone plans promise and diagnoses it zone by zone. Second, it shows with exact integer programmes that grid-based placement fills people but leaves living zones empty. Third, it compares minimum standards set by gu, living zone and dong under the same facility budget and shows that only the living-zone scale can fill every zone.

## 2. Literature review

### 2.1. Defining and contextualizing living zones

The living zone descends from the neighbourhood unit. Perry (1929) bounded a residential neighbourhood by the walking catchment of an elementary school and placed shops at its edge and community facilities at its centre; later guidelines varied the area, population and boundary of such units but kept the idea that daily services should be planned and counted within them (Park and Rogers, 2015). Central place theory supplied the complementary logic of service hierarchies and thresholds (Christaller, 1966). In Seoul, the 2030 Living Zone Plan formalised this tradition at two levels—five large living zones for regional functions and 116 local living zones for daily life—and set the local living zone as the unit in which daily public services are diagnosed and supplied (Seoul Metropolitan Government, 2018; Seoul Institute, 2019).

Why should services be planned by territory rather than by person? The public-finance and planning literatures give three reasons. Territorial justice holds that public services should be distributed among areas in proportion to their needs, so that no area is left without a basic level of provision (Boyne and Powell, 1991). Fiscal equivalence holds that the territory of a decision should match the territory of the people who benefit from it (Olson, 1969). Theories of multi-level governance add that task-specific, flexible jurisdictions sit alongside general-purpose ones (Hooghe and Marks, 2003), while the size of a unit shapes the capacity for local deliberation (Denters et al., 2014). None of these arguments is empirical in itself; each states a goal for which an intermediate unit may or may not be required.

Choosing a unit also shapes what can be seen. The modifiable areal unit problem means that the same underlying pattern produces different results at different scales and zonings (Openshaw, 1984), and the uncertain geographic context problem warns that residents' actual exposure rarely matches administrative boundaries (Kwan, 2012). Accessibility measured within administrative boundaries understates the services residents can reach across them (Tao et al., 2018). These problems are usually treated as sources of error; here they become the object of study, because a unit that hides deficits cannot be used to promise their removal.

### 2.2. Walkable service bundles and grid-based location planning

Research on the 15-minute city has turned the neighbourhood ideal into measurable indicators. Reviews list dozens of measures that differ in the services they include, the travel thresholds they use and the way they combine services (Papadopoulos et al., 2023). Logan et al. (2022) defined the x-minute city as the time within which a resident can reach the nearest of every essential amenity, a definition that treats services as a bundle that is complete only when every element is present. Abbiasov et al. (2024) showed with mobility data that people living in more complete neighbourhoods make more of their trips locally. The sufficiency perspective in transport justice gives the normative basis for such bundles: every person should reach at least a minimum of each essential service (Lucas et al., 2016; Martens, 2016; Pereira et al., 2017), and absolute thresholds of this kind are easier to communicate and monitor than relative ones (Jasso Chávez et al., 2026).

Facility location models provide the tools to close the gaps that such indicators reveal. The maximal covering location problem places a fixed number of facilities to maximise the population within a service distance (Church and ReVelle, 1974), and a large literature adds equity objectives that favour the worst-off (Marsh and Schilling, 1994; Ogryczak, 2000; Karsu and Morton, 2015) and measures the efficiency they cost (Bertsimas et al., 2011). Aggregating demand to zones introduces errors that fine grids avoid (Hillsman and Rhoda, 1978; Current and Schilling, 1990), which is one reason grid-based models have become the norm.

These models optimise over people—total coverage, or coverage weighted towards deprived residents. Whether their solutions leave whole territories unserved is not part of the objective and is rarely reported.

### 2.3. Research gaps in assessing the necessity of living zones and this study's contributions

Although both literatures bear on living-zone planning, three gaps limit their use for deciding whether living zones are needed. First, 15-minute city studies measure individual amenities or everyday commercial functions and seldom diagnose, zone by zone, the bundle of public services that living-zone plans actually promise. Second, location studies optimise total and person-based equity but do not test whether their solutions leave living zones empty—which is precisely what a zone-level plan cannot accept. Third, living-zone studies have asked whether official boundaries match mobility communities (Park et al., 2025; Park et al., 2026) but have not compared, under the same facility budget, which planning unit can actually carry a zone-level minimum standard.

To address these gaps, this study contributes by (1) measuring bundle completion for the six public-service domains of Seoul's living-zone plan and diagnosing it zone by zone; (2) showing with exact integer programmes that grid-based placement fills people but leaves living zones empty; and (3) comparing minimum standards set by gu, living zone and dong under the facility additions actually observed, together with a test of whether official living-zone boundaries cut walkable access less than random partitions.

## 3. Data and methods

### 3.1. Study area: Seoul

Seoul covers 605 km² and had 9.34 million residents in 2024 (9.64 million in 2019) on 30,785 populated 100 m grid cells. Its planning hierarchy is fully nested (Table 1, Fig. 1): 25 gu (mean population 373,515), 116 official living zones (80,499; range 21,165–148,376) and 424 administrative dong (22,023). Each living zone contains 3.7 dong on average (range 1–7), and each gu contains 4.6 living zones (range 3–7).

### 3.2. Data sources

**Population.** Residential population on the 100 m national grid for 2019 and 2024 (Statistics Korea, SGIS), used for the 2020 and 2025 analyses respectively.

**Walking travel times.** Cell-to-cell walking times on the OpenStreetMap pedestrian network at 4 km/h, computed for every origin–destination pair up to 30 minutes for 2020 and 2025.

**Facilities.** An inventory of 32 facility types for both years, geocoded to grid cells (584,766 records), supplemented by three layers needed for the plan's service domains: public sports facilities (Ministry of Culture, Sports and Tourism, 2019 and 2024), community child centres (Seoul open data, 2026 list) and parks (the 2018 park layer of the Seoul Living Zone Plan). The park and child-centre layers are held fixed for both years.

**Service bundles.** We compare three bundles (Table 2). (a) Everyday functions: the seven categories of the accessibility inventory (education, culture, childcare and welfare, personal services, retail, health, administration and safety). (b) The four amenities of Logan et al. (2022): pharmacy, supermarket, park and elementary school. (c) Planned public services: six of the seven local service domains of Seoul's 2030 Living Zone Plan—park, public library, senior leisure, youth and children, childcare and public sports—excluding parking. The six-domain bundle and its 10-minute threshold are a research operationalisation of the plan's domains and its 10-minute/800 m guideline, not a reproduction of an official indicator.

**Boundaries.** Administrative dong (424), official living zones (116), gu (25) and, for comparison, 116 mobility communities derived from daytime non-commuting origin–destination flows with the Leiden algorithm (Park et al., 2026).

### 3.3. Placement rules: grid-based versus zone-based

All experiments answer the same question: if Seoul adds the number of facilities it actually added between 2020 and 2025, where should they go? The budget N is the net increase in facility-occupied grid cells of each type (public library 31, senior facility 93, youth centre 11, public childcare centre 200, public sports facility 46; 381 in total for the bundle; for single facilities also cultural facility 32, public kindergarten 54 and community centre 8). It is an upper bound on additions, not a monetary budget. Candidate sites are populated or business-occupied cells without an existing facility of the same type.

**Grid-based rules** place facilities to optimise outcomes over people. (i) *Grid efficiency* maximises the population newly reached. (ii) *Grid vulnerability-weighted* gives extra weight to cells that lacked access before placement. (iii) For the bundle, an exact *maximal covering* integer programme maximises the population that completes the bundle:

$$\max \sum_i p_i z_i \quad \text{s.t.} \quad z_i \le \sum_{j} A^{s}_{ij} x_{sj} \;\; \forall i, \forall k \notin K_i, \qquad \sum_j x_{sj} \le N_s, \qquad x_{sj}\in\{0,1\},\; z_i\in[0,1] \tag{1}$$

where $p_i$ is the population of cell $i$, $K_i$ the domains already reached from $i$, $A^s_{ij}=1$ if a facility of type $s$ at $j$ is within the threshold of $i$, and $z_i$ indicates completion. We compare it with the exact solution of separate type-by-type covering problems, and with a coordinated heuristic whose objective $\sum_i p_i (c_i/6)^P$ rewards cells closer to completion ($P=2,4,8$; lower $P$ favours the most deprived).

**Zone-based rules** first meet a minimum standard in every unit of a chosen planning unit and then use the remaining facilities for efficiency. For single facilities the standard is a coverage share $\tau$ equal to 0.6 × the population-weighted median dong coverage of that facility, applied to gu, living zones or dong; a hybrid rule fills the living-zone standard and then places the rest with vulnerability weights. For the bundle, we add a minimum-completion constraint to (1):

$$\textstyle\sum_{i\in u} p_i z_i + \mathrm{pop}_u\, d_u \;\ge\; \tau_u\, \mathrm{pop}_u - \mathrm{base}_u \quad \forall u, \qquad d_u \ge 0 \tag{2}$$

with a penalty $M=50$ on the shortfall $d_u$ in the objective, so that standards are met first. We set $\tau=1\%$ and $5\%$, capped at the structural maximum of each unit. Fig. 2 summarises the framework.

### 3.4. Indices for evaluation and analytical procedure

#### 3.4.1. Evaluation indices

- **Bundle completion rate**: the share of residents who reach every domain of a bundle within the threshold, equivalent to the x-minute definition (Logan et al., 2022).
- **Zero-completion living zones**: the number of official living zones in which no resident completes the bundle.
- **Minimum-standard shortfall**: the number of units whose coverage (single facility) or completion (bundle) is below $\tau$.
- **Bottom-20 completion**: completion among the 20% of residents who reached the fewest domains before placement (ties weighted fractionally).
- **Boundary-restricted loss**: the decline in the population reaching a facility when residents may use only facilities inside their own unit.

#### 3.4.2. Analytical approach

For RQ1 we compute completion curves from 0 to 20 minutes and completion by living zone. For RQ2 we score every grid-based rule on three report cards—total access, bottom-20 access and the number of living zones below the minimum—for the seven single facilities and for the bundle. For RQ3 we apply zone-based rules to gu, official living zones and dong, and, for the bundle, to random 116-zone partitions (three draws) and to the 116 mobility communities. To test whether the official boundaries themselves matter, we compare their boundary-restricted loss with 150 random contiguous partitions into 116 zones under three generators (population-balanced, dong-balanced and unconstrained), and repeat the test after randomly relocating facilities 20 times. Exact integer programmes were solved with HiGHS; grid-based solutions reached optimality (gap 0), and the bundle minimum-standard models were solved within time limits of 1.5 h (gu, dong, random, mobility communities) and 4 h (official living zones).

## 4. Results

### 4.1. Data overview: service bundles in Seoul's living zones (RQ1)

Seoul's everyday functions are almost universally walkable (Table 3, Fig. 3). Within 15 minutes, 94.8% (2020) and 94.6% (2025) of residents reach all four amenities of Logan et al. (2022), and 73.1% and 77.3% reach all seven everyday categories; five of the seven categories are within 15 minutes of more than 99% of residents. Among those who do not complete the everyday bundle, 86% and 84% lack only one category.

The public services that the living-zone plan promises are a different matter. Only 3.7% (2020) and 5.3% (2025) of residents can reach all six domains within 10 minutes, and even at 15 minutes the shares rise only to 20.9% and 27.4%. The gap is not an artefact of the threshold: at the same 10 minutes, 37.2% and 39.9% complete the everyday bundle. Non-completion is also deep rather than marginal: 83% and 80% of non-completing residents lack two or more domains, most often public sports (80%) and the library (70%); childcare, by contrast, is reached by 98%.

What is missing is missing in places. In 50 (2020) and 38 (2025) of the 116 living zones, not a single resident completes the bundle, and in 91 and 73 fewer than 5% do (Fig. 5a). Seoul's everyday commercial functions are almost universally walkable, but the public services that the living-zone plan promises are not: in more than a third of living zones, no resident can reach all six within 10 minutes.

### 4.2. Grid-based versus zone-based placement (RQ2)

#### 4.2.1. Single facilities

Grid-based placement does what it is designed to do (Table 4a, Fig. 4). Vulnerability-weighted placement reaches the most deprived residents better than the living-zone standard in 12 of 14 facility–year combinations (for libraries in 2025, 57.9% of vulnerable residents reached against 53.2% under the living-zone standard), at an efficiency cost of about 0.1 percentage points. But it barely changes the number of living zones left below the minimum: for libraries, 11 under grid efficiency and 9 under vulnerability weighting (2020); for public kindergartens, 14 and 13. Vulnerability-weighted grid placement reaches deprived residents best, yet it leaves nearly every under-served living zone under-served.

#### 4.2.2. Service bundle

The same holds, more starkly, for the bundle (Table 4b, Fig. 6). Maximising bundle completion exactly raises it to 22.8% (2020) and 24.2% (2025), 55% and 47% more than the exact type-by-type solution (14.7% and 16.5%)—coordinating the bundle pays. Yet 18 and 14 living zones still have no resident completing it (Fig. 5b). Weighting the objective towards deprived residents does not help: the coordinated heuristic with $P=2$ reaches 5.8% and 6.3% of the bottom-20 group, the highest of all rules, but leaves 21 and 19 living zones at zero. Optimising the grid, whether for total completion or for the most deprived residents, does not fill places: 14 to 21 living zones remain with no resident completing the bundle.

#### 4.2.3. People and places

The two goals pull in different directions. The exact total-maximising solution reaches only 0.1% and 0.2% of the bottom-20 group, because cells that lack many domains are rarely worth completing when the objective counts heads. For single facilities, the hybrid rule—living-zone standard first, vulnerability weights for the rest—recovers vulnerable access while keeping every zone above the minimum (public childcare 42.6% in both years against 42.6% and 42.8% under vulnerability weighting; public kindergarten 35.4% and 36.8% against 35.3%). Filling people and filling places are different tasks; the first is done on the grid, the second requires a zone-level standard.

### 4.3. Planning units for minimum standards (RQ3)

#### 4.3.1. Gu

A standard set by gu changes almost nothing (Table 4, Fig. 6). For the bundle, zero-completion living zones remain at 18 (2020) and 12 (2025) under a 5% gu standard, and the cost in citywide completion is at most 0.05 percentage points—a sign that the standard does no work. For libraries, the gu standard leaves 10 and 7 living zones below the minimum, the same as grid efficiency. Gu are large enough that their averages already exceed the standard while the living zones inside them remain empty; aggregation to gu also hides more of the deficit than any other unit (share of under-served residents in units that meet the standard on average: dong 0.21, living zones 0.34, gu 0.43, libraries 2020).

#### 4.3.2. Dong

A standard set by dong cannot be met. For libraries, meeting the dong standard requires 68 (2020) and 58 (2025) new facilities by exact solution, against the 31 actually added; living zones require 21 and 18, gu 2. For the bundle, a 5% dong standard costs 4.6–5.2 percentage points of citywide completion and still leaves 198–221 of 424 dong below the standard, and the number of zero-completion living zones does not fall (20 and 16). Across the seven facilities, the living-zone scale lies within the range in which the observed additions can meet a minimum for four (library, cultural facility, public kindergarten, community centre), whereas the dong scale lies outside it for six.

#### 4.3.3. Living zones

Only a standard set at the living-zone scale fills places. For single facilities, the living-zone standard brings the number of living zones below the minimum to zero for six of seven facilities in both years; the exception, youth centres, has only 11 additions and falls from 21 to 7. For the bundle, a 5% living-zone standard reduces zero-completion living zones from 18 to 3 (2020) and from 14 to 2 (2025), and zones below 5% from 33 to 9 and from 29 to 5 (Fig. 5c), at a cost of 2.8 and 2.1 percentage points of citywide completion (1.3 and 0.6 points under a 1% standard). The effect comes from the scale: random 116-zone partitions reduce zero-completion zones to 5–7 and mobility communities to 4, whereas gu and dong do not reduce them at all. Because zero-completion is counted in official living zones, standards set on the same zones are favoured in this count; the scale result, not the ranking among 116-zone partitions, is the core finding. Only a standard set at the living-zone scale fills places: zero-completion living zones fall from 14 to 2, at a cost of about two percentage points of citywide completion.

#### 4.3.4. Official boundaries

Official living zones are not an arbitrary way to draw 116 zones. When residents may use only facilities inside their own zone, the population reaching a library falls by 10.0 percentage points with official boundaries but by 13.9 points (median) with random 116-zone partitions (2020); the difference holds for cultural facilities, kindergartens and childcare, in both years and under all three random generators ($p \le 0.04$). It also survives random relocation of facilities: in all 20 relocations of each of seven facilities, official boundaries cut less access than the random median, so the result does not depend on the observed facility pattern alone. The share of residents whose 15-minute walking catchment crosses a zone boundary is 0.84 for official living zones against 0.89 for random partitions, lower than every one of 40 draws. And a minimum standard set on official living zones reduces shortfalls in mobility communities that were not used in placement more than a standard set on random zones (six of seven facilities). Official living zones cut walkable access less than random partitions of the same number, consistent with their close alignment with mobility communities (Park et al., 2026).

## 5. Discussion and conclusion

This study tested whether living zones are necessary for Seoul's walkable public services. The answer has three parts. The services the living-zone plan promises are missing in places, not only for people: in more than a third of living zones no resident can reach all six within a 10-minute walk. Placing new facilities on the grid fills people but not places: whether it maximises total completion or targets the most deprived residents, it leaves 14 to 21 living zones with no resident completing the bundle. And only a minimum standard set at the living-zone scale fills those places, at a cost of 0–3 percentage points of citywide access; the same standard set by gu changes nothing, and set by dong it cannot be met.

Why is grid optimisation not enough? Grid objectives send each facility to the cells where it completes or helps the most residents. A living zone that lacks several domains at once needs several facilities before any of its residents completes the bundle, so under any person-based objective it loses out to places where one facility is enough. The empty zones are not a failure of optimisation; they are what person-based optimisation produces. The point extends beyond Seoul. Debates on the 15-minute city have warned that average accessibility can mask inequality (Mouratidis, 2024; Willberg et al., 2023); our results show that even person-based equity objectives can mask territorial deficits. A city that promises service to every neighbourhood cannot keep that promise with person-based indicators alone.

Why living zones, and not gu or dong? Gu are large enough to average away the deficits of the living zones inside them, which is why a gu standard costs almost nothing and achieves almost nothing. Dong are small enough that a standard in each of 424 units exceeds the facilities a city actually adds. The living-zone scale lies between these limits: random partitions at the same scale also reduce empty zones, showing that the scale itself does the work, and the official boundaries cut walkable access less than random ones, consistent with their alignment with residents' mobility (Park et al., 2026). These findings give empirical content to arguments for intermediate units that have so far been normative—territorial justice (Boyne and Powell, 1991) and fiscal equivalence (Olson, 1969): if the goal is that every territory receives a minimum, the territory must be defined at a scale where the minimum is both visible and attainable.

For planning practice, the results suggest a division of labour. Accessibility should be measured and facilities located on the grid, which is precise and serves people best. Promises and monitoring should be made by living zone, which is the only unit at which a minimum for every place can be met. Concretely, a living-zone plan should state a minimum bundle standard for each local living zone, meet it first, and allocate the remaining facilities by grid-based vulnerability weighting; reporting progress by gu would conceal the zones that remain empty.

Several limitations qualify these conclusions. The goal of a minimum standard in every living zone is taken from Seoul's plan; it is a normative premise, and if only person-based equity matters, grids suffice. The bundle minimum-standard models were solved within time limits (optimality gaps of 3–49%), and two or three living zones remained below the standard; longer runs improved the solutions, so the residual is likely computational. For the bundle we did not test the hybrid rule that combines a living-zone standard with vulnerability weighting, which recovered vulnerable access for single facilities. The facility budget is the observed increase in occupied cells, not a cost-based budget, and land, capacity and age-specific demand are not modelled. The six-domain bundle and 10-minute threshold are a research operationalisation; the park and child-centre layers are held fixed; and the analysis covers one city at two points in time.

Grids fill people, not places. Seoul's living-zone plan promises to fill every living zone with daily public services, and only a minimum standard set at the living-zone scale does so; standards set by gu hide the gaps, and standards set by dong cannot be met. Living zones are necessary for that promise, and neither grids, gu nor dong can substitute for them.

---

## References

Abbiasov, T., Heine, C., Sabouri, S., Salazar-Miranda, A., Santi, P., Glaeser, E., Ratti, C., 2024. The 15-minute city quantified using human mobility data. Nature Human Behaviour 8, 445–455. [verify]

Allam, Z., Nieuwenhuijsen, M., Chabaud, D., Moreno, C., 2022. The 15-minute city offers a new framework for sustainability, liveability, and health. The Lancet Planetary Health 6 (3), e181–e183. https://doi.org/10.1016/S2542-5196(22)00014-6

Berlin Senate Department for Urban Development, Building and Housing, 2021. Lebensweltlich orientierte Räume (LOR) in Berlin. Berlin.de.

Bertsimas, D., Farias, V.F., Trichakis, N., 2011. The price of fairness. Operations Research 59 (1), 17–31. https://doi.org/10.1287/opre.1100.0865

Boyne, G., Powell, M., 1991. Territorial justice: A review of theory and evidence. Political Geography Quarterly 10 (3), 263–281. https://doi.org/10.1016/0260-9827(91)90038-V

Christaller, W., 1966. Central Places in Southern Germany (C.W. Baskin, Trans.). Prentice-Hall, Englewood Cliffs.

Church, R., ReVelle, C., 1974. The maximal covering location problem. Papers of the Regional Science Association 32 (1), 101–118. https://doi.org/10.1007/BF01942293

Current, J., Schilling, D., 1990. Analysis of errors due to demand data aggregation in the set covering and maximal covering location problems. Geographical Analysis 22 (2), 116–126. https://doi.org/10.1111/j.1538-4632.1990.tb00199.x

Denters, B., Goldsmith, M., Ladner, A., Mouritzen, P.E., Rose, L.E., 2014. Size and Local Democracy. Edward Elgar, Cheltenham.

Hillsman, E.L., Rhoda, R., 1978. Errors in measuring distances from populations to service centers. Annals of Regional Science 12, 74–88. https://doi.org/10.1007/BF01286124 [verify volume]

Hooghe, L., Marks, G., 2003. Unraveling the central state, but how? Types of multi-level governance. American Political Science Review 97 (2), 233–243.

Jasso Chávez, J.A., Kelly, N., Pereira, R.H.M., Boisjoly, G., Manaugh, K., 2026. Revisiting sufficientarianism in accessibility research: A review of accessibility poverty. Transport Reviews. https://doi.org/10.1080/01441647.2026.2720413

Karsu, Ö., Morton, A., 2015. Inequity averse optimization in operational research. European Journal of Operational Research 245 (2), 343–359. https://doi.org/10.1016/j.ejor.2015.02.035

Kwan, M.-P., 2012. The uncertain geographic context problem. Annals of the Association of American Geographers 102 (5), 958–968. https://doi.org/10.1080/00045608.2012.687349

Logan, T.M., Hobbs, M.H., Conrow, L.C., Reid, N.L., Young, R.A., Anderson, M.J., 2022. The x-minute city: Measuring the 10, 15, 20-minute city and an evaluation of its use for sustainable urban design. Cities 131, 103924. https://doi.org/10.1016/j.cities.2022.103924

Lucas, K., van Wee, B., Maat, K., 2016. A method to evaluate equitable accessibility: Combining ethical theories and accessibility-based approaches. Transportation 43 (3), 473–490. https://doi.org/10.1007/s11116-015-9585-2

Marsh, M.T., Schilling, D.A., 1994. Equity measurement in facility location analysis: A review and framework. European Journal of Operational Research 74 (1), 1–17. https://doi.org/10.1016/0377-2217(94)90200-3

Martens, K., 2016. Transport Justice: Designing Fair Transportation Systems. Routledge, New York.

Moreno, C., Allam, Z., Chabaud, D., Gall, C., Pratlong, F., 2021. Introducing the "15-minute city": Sustainability, resilience and place identity in future post-pandemic cities. Smart Cities 4 (1), 93–111. https://doi.org/10.3390/smartcities4010006

Mouratidis, K., 2024. Time to challenge the 15-minute city: Seven pitfalls for sustainability, equity, livability, and spatial analysis. Cities 153, 105274. https://doi.org/10.1016/j.cities.2024.105274

Office for Government Policy Coordination et al., 2019. Three-year plan for Life SOC (2020–2022). Policy briefing, 15 April 2019. [Korean]

Ogryczak, W., 2000. Inequality measures and equitable approaches to location problems. European Journal of Operational Research 122 (2), 374–391. https://doi.org/10.1016/S0377-2217(99)00240-4

Olson, M., 1969. The principle of "fiscal equivalence": The division of responsibilities among different levels of government. American Economic Review 59 (2), 479–487.

Openshaw, S., 1984. The Modifiable Areal Unit Problem. Concepts and Techniques in Modern Geography 38. Geo Books, Norwich.

Papadopoulos, E., Sdoukopoulos, A., Politis, I., 2023. Measuring compliance with the 15-minute city concept: State of the art, major components and further requirements. Sustainable Cities and Society 99, 104875. https://doi.org/10.1016/j.scs.2023.104875

Park, J., Eom, S., Lee, M.-H., 2026. Benchmarking living-zone plans with mobility community detection: Evidence from Seoul's mobile-phone-based mobility data. Journal of Transport Geography 135, 104753. https://doi.org/10.1016/j.jtrangeo.2026.104753

Park, J., Lee, M.-H., Eom, S., 2025. A study on verifying living zone boundaries using big data-based community detection. CUPUM 2025 (Computational Urban Planning and Urban Management). [verify proceedings details]

Park, Y., Rogers, G.O., 2015. Neighborhood planning theory, guidelines, and research: Can area, population, and boundary guide conceptual framing? Journal of Planning Literature 30 (1), 18–36. https://doi.org/10.1177/0885412214549422

Pereira, R.H.M., Schwanen, T., Banister, D., 2017. Distributive justice and equity in transportation. Transport Reviews 37 (2), 170–191. https://doi.org/10.1080/01441647.2016.1257660

Perry, C.A., 1929. The Neighborhood Unit. Regional Survey of New York and Its Environs, Vol. VII, Monograph I. Regional Plan of New York and Its Environs, New York.

Seoul Institute, 2019. White Paper on the 2030 Seoul Living Zone Plan. Seoul Metropolitan Government. [Korean]

Seoul Metropolitan Government, 2018. 2030 Seoul Living Zone Plan. Seoul Urban Planning Portal. https://urban.seoul.go.kr/view/html/PMNU3040000001 [Korean]

Talen, E., Anselin, L., 1998. Assessing spatial equity: An evaluation of measures of accessibility to public playgrounds. Environment and Planning A 30 (4), 595–613. https://doi.org/10.1068/a300595

Tao, Z., Cheng, Y., Zheng, Q., Li, G., 2018. Measuring spatial accessibility to healthcare services with constraint of administrative boundary: A case study of Yanqing District, Beijing, China. International Journal for Equity in Health 17, 7. https://doi.org/10.1186/s12939-018-0720-5

Teixeira, J.F., Silva, C., Seisenberger, S., Büttner, B., McCormick, B., Papa, E., Cao, M., 2024. Classifying 15-minute Cities: A review of worldwide practices. Transportation Research Part A: Policy and Practice 189, 104234. https://doi.org/10.1016/j.tra.2024.104234

Willberg, E., Fink, C., Toivonen, T., 2023. The 15-minute city for all? Measuring individual and temporal variations in walking accessibility. Journal of Transport Geography 106, 103521. https://doi.org/10.1016/j.jtrangeo.2022.103521

---

## Figure captions

**Fig. 1.** Study area: Seoul's 25 gu, 116 official living zones and 424 administrative dong.

**Fig. 2.** Analytical framework. The same facility budget (net additions 2020→2025) is placed under grid-based and zone-based rules and scored on three report cards.

**Fig. 3.** Bundle completion. (a, b) Share of residents completing each bundle by walking time, 2020 and 2025; dotted lines mark 10 and 15 minutes. (c) Number of missing domains among non-completing residents, 2025.

**Fig. 4.** Official living zones below the minimum standard after placing the observed additions of each facility, by placement rule. (a) 2020, (b) 2025.

**Fig. 5.** Share of residents completing the six-domain bundle within 10 minutes, by official living zone, 2025. (a) Before placement; (b) after grid-optimised placement (exact maximal covering); (c) after placement under a 5% living-zone minimum standard.

**Fig. 6.** Zero-completion official living zones after placing the 381 additions under each rule, (a) 2020 and (b) 2025. Random and mobility-community partitions were run for 2025 only.

## Tables

- Table 1. Planning hierarchy of Seoul → `manuscript/tables/Table1_planning_hierarchy.md`
- Table 2. Planned public-service bundle: domains, facility cells and placement budget → `Table2_bundle_domains.md`
- Table 3. Bundle completion rate by walking-time threshold → `Table3_bundle_completion.md`
- Table 4. Three report cards by placement rule: (a) single facilities, (b) bundle → `Table4_report_cards.md`
