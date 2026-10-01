# -*- coding: utf-8 -*-
"""영문 원고 본문(Applied Geography 형식). 숫자는 모두 {키}로 두고 a06_manuscript.py가 결과 파일에서 채운다.
블록: ('h1'|'h2', 제목), ('p', 문단), ('pc', 수식 뒤 이어지는 문단), ('eq', 수식 한 줄), ('table', 표 키), ('fig', 그림 키).
문체(2026-10-01): 대학생이 읽을 수 있는 쉬운 어휘, 문장 중앙값 22~25단어, 발견을 먼저 말하고 조건은 뒤에 한 번.
용어는 JTG 게재본(living-zone plan, mobility communities, benchmark, mismatch, self-containment)과 KPA(boundary dongs,
reassignment to an adjacent zone)를 따른다. 줄임말은 처음 쓸 때 소문자 전체 용어 뒤 괄호로 정의한다(AG 게재 논문 10편 대조).
"""

TITLE = 'Following trips, keeping services: Mobility-guided reassignment of boundary dongs in Seoul’s living-zone plan and within-zone walkable service coverage'

ABSTRACT = (
    'Cities increasingly use mobility data to redraw planning zones so that each zone holds more of its residents’ trips. But a living zone is also the unit in which a city counts and supplies everyday services. Moving a boundary to follow trips may leave residents’ walkable facilities outside their zone. We test whether this happens in Seoul’s official living-zone plan in 2020 and 2025. We combine daytime non-work trips between neighbourhoods (dongs) estimated from mobile-phone data, a register-based inventory of everyday facilities in seven categories, and a walking network. Our measure is the number of residents who can walk to a type of service only outside their own zone. Moving boundary dongs to the zones their trips go to kept more trips inside zones and lowered this number. Moving the same number at random raised it in all 100 simulated runs. The official plan itself left fewer residents outside than almost all alternative maps with similar zone sizes and shapes. Trips from boundary dongs went mainly to adjacent zones that held more of their walkable health, retail and personal-service facilities. In Seoul, following trips did not cost services, because trips and facilities pointed to the same places. Mobility data can therefore be used to adjust an existing living-zone plan, as long as within-zone service coverage is checked together with self-containment. This holds when the number of zones is fixed and zone population and shape are not constrained; with both constraints, it held in one of the two years.')

KEYWORDS = ['Living-zone plan', 'Boundary review', 'Walking accessibility', 'Mobility communities', 'Redistricting ensembles', 'Mobile-phone mobility data', 'Seoul']

HIGHLIGHTS = [
    'Reassigning boundary dongs along trips kept walkable services inside Seoul’s zones',
    'Random reassignment of the same extent pushed services out in every simulated path',
    'Self-containment and within-zone service coverage improved together',
    'Seoul’s official zones beat almost all size- and shape-matched alternative maps',
    'Trips from boundary dongs go where their walkable health, retail and services are',
]

BODY = [
    ('h1', '1. Introduction'),
    ('p', 'Planning by neighbourhood is back at the centre of urban policy. The 15-minute city and similar ideas ask that the '
          'services people need every day be within walking distance of home (Moreno et al., 2021; Allam et al., 2022; Logan et '
          'al., 2022). Behind these ideas is an older planning tool, which we call a living zone. A living zone is an area smaller '
          'than a municipality and larger than a block, inside which a set of everyday services is planned, counted and supplied. '
          'The idea goes back to Perry’s (1929) neighbourhood unit, sized by the walking distance to an elementary school and '
          'equipped with shops, open space and community facilities. It continues in the neighbourhood planning guidelines '
          'reviewed by Park and Rogers (2015) and in Talen’s (2003) view of neighbourhoods as service providers whose walkable '
          'supply can be measured.'),
    ('p', 'Cities use planning areas of several sizes. Berlin’s lifeworld-oriented spaces are the spatial reference for its social '
          'planning and population monitoring (Berlin Senate Department for Urban Development, Building and Housing, 2021). The '
          '2016 London Plan used sub-regions to monitor the plan and to coordinate across boroughs (Greater London Authority, '
          '2016). Greater Sydney’s 2018 strategy grouped the region into three cities and five districts around the aim that '
          'residents live within 30 minutes of jobs and services (Greater Sydney Commission, 2018). These units differ in size '
          'and purpose. Seoul’s living-zone plan, adopted under the city’s 2030 planning framework, has five regional and 116 '
          'local living zones. The city uses the local zones to identify service shortfalls and to set local priorities (Seoul '
          'Metropolitan Government, 2018). None of these examples promises that every everyday service can be found inside each '
          'boundary. This paper studies the local living zone and its role in identifying service shortfalls.'),
    ('p', 'Most living zones were drawn from administrative boundaries, local knowledge and negotiation, not from data on how '
          'residents travel. Large mobility datasets now make it possible to benchmark an official plan against mobility '
          'communities, that is, groups of areas that exchange many trips with each other. Such benchmarks show that official '
          'zones and mobility communities often do not match, in Seoul as in other cities (Shen & Batty, 2019; Park et al., '
          '2026). The obvious response is to move boundaries towards the flows. This follows a long tradition in functional '
          'regionalisation, in which a region is considered good when most of the trips that start in it also end in it (Smart, '
          '1974; Coombes et al., 1986; Karlsson & Olsson, 2006).'),
    ('p', 'This response has a possible cost that has received little attention. A living zone is not only a container of trips. '
          'It is also the unit in which a city counts the facilities that serve its residents. When a plan identifies service '
          'shortfalls zone by zone, a resident whose nearest clinics or libraries all lie just across the boundary appears, in the '
          'zone’s records, to lack that service. Moving a boundary to capture more trips can therefore push walkable facilities '
          'out of residents’ zones, even though nothing has changed on the ground. A revision that looks better in terms of '
          'self-containment may then look worse by the standard the plan was made for. Accessibility research has mostly treated '
          'boundaries as a source of measurement error (Fotheringham & Wong, 1991; Kwan, 2012; Gao et al., 2017). It has rarely '
          'treated them as planning objects whose revision changes which services residents are counted as having.'),
    ('p', 'This paper tests whether that cost is real. We ask whether the facilities residents can walk to stay inside their zones '
          'when the boundary dongs of Seoul’s living-zone plan are reassigned along observed trips. We study the 116 official '
          'living zones and the 424 administrative neighbourhoods (dongs) that make them up, in 2020 and 2025. We combine daytime '
          'non-work origin–destination trips estimated from mobile-phone data, an inventory of everyday facilities in seven '
          'categories built from public registers, and a walking network. Within-zone service coverage is measured by the number '
          'of residents who can reach a type of service within a 15-minute walk only by leaving their own zone. We ask three '
          'questions. Q1: does reassigning boundary dongs along observed trips raise or lower that number, compared with the same '
          'number of random reassignments? Q2: how does the official plan compare with a large set of alternative maps that follow '
          'the same size and shape rules, generated with methods from electoral redistricting (DeFord et al., 2021)? Q3: do trips '
          'from boundary dongs go towards the adjacent zones that hold more of the facilities their residents can walk to?'),
    ('p', 'The answers are the same in both years. Reassigning boundary dongs along trips raised self-containment and lowered the '
          'number of residents left outside their zone’s walkable services. Random reassignment of the same extent raised that '
          'number in every simulated run. The official plan left fewer residents outside than almost every alternative map. '
          'Trips from boundary dongs went towards the adjacent zones where their walkable facilities were. In Seoul, following '
          'trips did not cost services, because trips and facilities pointed to the same places. The paper makes two '
          'contributions. First, it treats within-zone service coverage as a property of a boundary, separate from accessibility '
          'itself, and shows how to measure it with standard data. Second, it judges boundary revisions against clear benchmarks, '
          'namely random revisions of the same extent and large sets of alternative plans, rather than on their own. Sections 2 to 5 take the three questions in the same order.'),
    ('h1', '2. Literature review'),
    ('h2', '2.1. Living zones as service units and the boundary problem'),
    ('p', 'Proximity-based planning has renewed interest in such units. Studies of the 15-minute city measure whether residents can '
          'reach several types of amenity within a fixed walking time (Weng et al., 2019; Moreno et al., 2021; Logan et al., '
          '2022; Staricco, 2022), and how this differs between people and over the day (Willberg et al., 2023). Critics note that '
          'proximity targets say little about capacity, quality or who benefits (Mouratidis, 2024). Almost all of these studies '
          'measure outwards from the home and ignore planning boundaries. This leaves aside a question that matters to planners who work zone by zone: whether the '
          'service a resident can reach is one that the plan counts as theirs.'),
    ('p', 'Work on public finance and territorial justice explains why that question matters. The principle of fiscal equivalence '
          'says that the area that provides a service should match the population that benefits from it (Olson, 1969). '
          'Territorial justice asks whether services are shared between areas in line with their needs (Boyne & Powell, 1991). '
          'Seoul’s living-zone plan treats zones in the same way: facility shortfalls are identified zone by zone, and each zone plan sets priorities for what should be '
          'provided within it (Seoul Metropolitan Government, 2018). In this sense, a living zone is a promise that a set of '
          'everyday services can be found inside it. Whether a boundary keeps that promise depends on the boundary, not only on '
          'where facilities are. We use this idea as a counting rule for the analysis. We do not claim that the plan guarantees '
          'every category within each zone, or that residents cannot use services across boundaries.'),
    ('p', 'Accessibility has been measured in many ways since Hansen (1959), from counts of reachable opportunities to gravity-based '
          'and utility-based measures (Handy & Niemeier, 1997; Geurs & van Wee, 2004; Páez et al., 2012). It is the standard tool '
          'for assessing spatial equity in service provision (Talen & Anselin, 1998). In this literature, boundaries appear mainly '
          'as a problem. Results change with the zones used to aggregate data (Openshaw, 1984; Fotheringham & Wong, 1991), the '
          'area that shapes a person’s daily experience is uncertain (Kwan, 2012), aggregating demand to zone centres distorts '
          'distances (Hillsman & Rhoda, 1978), and supply just outside a study area is easily missed (Gao et al., 2017). Tao et '
          'al. (2018) showed that limiting healthcare supply to residents’ own administrative units changes measured '
          'accessibility considerably. They argued that this limit reflects how services are actually organised there.'),
    ('p', 'We take this last point one step further. When a plan allocates services by zone, the gap between what residents can '
          'reach and what they can reach within their zone is not an error to be corrected. It is exactly what the boundary '
          'decides. We call the extent to which reachable services lie inside a resident’s own zone within-zone service '
          'coverage. We call the residents for whom some reachable category of service lies entirely outside their zone the '
          'excluded population.'),
    ('h2', '2.2. Functional regions, mobility communities and boundary review'),
    ('p', 'The main alternative to drawing zones for administrative convenience is to derive them from interaction. Functional '
          'regionalisation groups areas so that most trips that start in a region also end there. Smart (1974) and Coombes et al. '
          '(1986) set out the self-containment rules that still underlie British travel-to-work areas (Coombes & Bond, 2008), and '
          'Karlsson and Olsson (2006) reviewed the theory and methods. Later work treated the task as a network problem. Farmer and '
          'Fotheringham (2011) defined functional regions as communities in a flow network, Ratti et al. (2010) redrew the map of '
          'Great Britain from telephone links, and Halás et al. (2015) and Klapka et al. (2020) refined rule-based and graph-based '
          'methods. Community detection by modularity, which groups areas that exchange more trips with each other than expected by '
          'chance (Newman, 2006), and its refinements (Traag et al., 2019) are now standard tools. How to treat trips within an area '
          '(He et al., 2020) and whether standard modularity suits spatial interaction data (Martínez-Bernabéu & Casado-Díaz, '
          '2021) are still debated.'),
    ('p', 'The same methods have been used to review service areas and planning zones. Wang et al. (2021) drew hospital service '
          'areas from patient flows under spatial constraints, and Shen and Batty (2019) derived London’s functional regions as '
          'perceived from commuting. In Seoul, Park et al. (2026) benchmarked the official living-zone plan against mobility '
          'communities detected in mobile-phone trip networks. They found that many zones align, but that several districts show '
          'systematic mismatches with weaker internal connections and lower self-containment. All of this work judges how well a '
          'set of zones fits its flows: a region is good if it holds much of its own interaction. To our knowledge, no study has '
          'examined what happens to the services a planning zone is meant to contain when its boundary moves along the flows. Nor '
          'has any study compared flow-guided reassignment with reassignment of the same extent made without flow information. '
          'That comparison is our first question.'),
    ('h2', '2.3. Judging a plan against its alternatives'),
    ('p', 'A single plan’s coverage value means little on its own. Research on electoral redistricting faced the same problem. It '
          'solved it by comparing an adopted plan with large sets, or ensembles, of alternative plans that follow the same rules. '
          'Chen and Rodden (2013) used simulated plans to separate the effect of where voters live from the effect of deliberate '
          'design. Herschlag et al. (2020) used Markov chain sampling to evaluate North Carolina’s districts. DeFord et al. (2021) '
          'introduced the recombination (ReCom) chain, which creates a new plan by merging two adjacent districts and splitting '
          'them again along a random spanning tree. Territory design in operations research deals with similar problems under '
          'balance and compactness requirements (Kalcsics et al., 2005), and zone design in geography has long explored how many '
          'different zonings a set of rules allows (Openshaw & Rao, 1995). We borrow two ideas from this work. A revision should '
          'be judged against revisions of the same extent made without the information that guided it; this shapes the random '
          'benchmark in Section 3.2. And a plan should be judged against the plans it could have been, which is our second '
          'question.'),
    ('h2', '2.4. Trips and the location of everyday services'),
    ('p', 'The third question asks whether trips and walkable facilities point to the same places. Accessibility has long been '
          'linked to where activities are located (Hansen, 1959). Alexander et al. (2015) estimated trips by broad purpose and '
          'time of day from mobile-phone data, separating home-based work, home-based other and non-home-based trips. In '
          'Barcelona, Graells-Garrido et al. (2021) found that places with better access to education and retail received more '
          'visits, although the strength and direction of this link varied across the city. These studies give reason to examine '
          'where trips and reachable services lie relative to each other. They do not show that boundary changes based on mobility '
          'keep services inside zones. If trips go where services are, a boundary drawn around trips should keep services inside '
          'rather than push them out. Whether this holds at the boundaries of an existing plan, and for which services, has not '
          'been tested.'),
    ('h2', '2.5. Gaps and research questions'),
    ('p', 'Three gaps follow from this review. Flow-based revision is judged by self-containment alone. A plan’s coverage is rarely compared with the plans it could have been. And the spatial link between trips and walkable services at plan boundaries has not been tested. Questions Q1 to Q3 in Section 1 address these gaps in turn. Q3 also points to the likely reason for the first two results: if trips and facilities point to the '
          'same adjacent zone, a dong moved along its trips brings its facilities with it.'),
    ('h1', '3. Data and methods'),
    ('h2', '3.1. Study area, data and indicators'),
    ('p', 'Seoul’s 2024 population grid counts {pop25m} million residents in 25 autonomous districts (gu) and 424 dongs. The '
          'living-zone plan groups the dongs into 116 local living zones, each within a single gu (Fig. 1). We assign each dong '
          'to the official zone it overlaps most. Dong boundaries are kept at their July 2023 form in both years, so that plans '
          'differ only in which zone each dong belongs to. Table 1 summarises the data.'),
    ('fig', 'Fig1'),
    ('p', 'Trips come from the Seoul Living Mobility Dataset, in which the city estimates origin–destination flows between dongs '
          'from mobile-phone signals. We use January 2020 and January 2025, all days of the week, and trips arriving between 09:00 '
          'and 20:59. We remove trips between home and workplace, so that the flows describe daytime activities other than '
          'commuting. Values hidden for privacy are set to zero, and only trips with both ends in Seoul are kept. Trips that start '
          'and end in the same dong are included. The data contain {od20m} million trips in 2020 and {od25m} million in 2025.'),
    ('p', 'Residents are represented by the 100 m population grid of Statistics Korea for 2019 and 2024. Facilities come from an '
          'inventory we built from national and city registers, including business licence records, education, welfare, health and '
          'culture registers, and lists of public offices. It covers 27 facility types in seven categories: education, childcare '
          'and welfare, health, culture, civic and safety services, retail, and personal services (Table A.1). Each facility is '
          'placed in a 100 m grid cell and dated as close to the end of 2019 and of 2024 as its source allows. Sports businesses '
          'were excluded because their records could not be made consistent between the two years. The analysis uses {fac20} '
          'facility records in 2020 and {fac25} in 2025, located in {cell20} and {cell25} grid cells.'),
    ('p', 'Walking times are calculated on OpenStreetMap road data dated 1 January 2020 and 1 January 2025, clipped to Seoul with a '
          '2 km buffer. We keep paths that can be used on foot, ignore one-way restrictions and assume a walking speed of 4 km/h. '
          'The time between two cells is the shortest walking time between the network points nearest to their centres. A cell '
          'counts as reachable from another if this time is 15 minutes or less.'),
    ('table', 'T1'),
    ('p', 'Within each year, trips, population, facilities and the walking network are fixed, and only the assignment of dongs to '
          'zones changes. Differences between 2020 and 2025 combine changes in all inputs, so we do not read them as trends. The '
          'second year checks whether the same pattern appears with a different set of inputs.'),
    ('p', 'We calculate two indicators for every plan. Let o index populated 100 m cells with population p_o, let c index the seven '
          'facility categories, and let b be a plan that assigns each dong, and therefore each cell, to a zone. Let r_oc = 1 if a '
          'cell with a facility of category c can be reached from o within 15 minutes, and r_oc^b = 1 if such a cell can be '
          'reached and lies in the same zone as o under plan b. The walking route may pass through other zones; only the location '
          'of the destination matters. The population of cell o is excluded under plan b if at least one category can be reached '
          'but not within its own zone:'),
    ('eq', 'EQ1'),
    ('p', 'Each resident is counted once, however many categories are affected. A category that a resident cannot reach at all does '
          'not count towards L, because no boundary can fix a lack of access; such a resident may still be counted through another '
          'category. L therefore measures how much of the walkable supply a plan places outside residents’ zones. For a revised '
          'plan b compared with the official plan b_0, the change ΔL = N − R separates residents who become excluded (N) from '
          'those who stop being excluded (R). This matters because large gains and losses can cancel out.'),
    ('p', 'Self-containment is measured by the internal flow ratio (IFR), the share of trips between Seoul dongs that start and end '
          'in the same zone:'),
    ('eq', 'EQ3'),
    ('pc', 'where f_ij is the number of trips from dong i to dong j. L is a counting measure: it records which reachable services a '
          'plan counts as inside a resident’s zone. It does not record which services residents actually use, and it does not '
          'mean that they cannot use services outside their zone.'),
    ('h2', '3.2. Flow-guided and random reassignment of boundary dongs (Q1)'),
    ('p', 'We answer the first question by comparing two kinds of reassignment path. A reassignment moves one dong to an adjacent '
          'zone in the same gu; two dongs are adjacent if their boundaries touch at any point (queen contiguity). A move is allowed '
          'only if the zone the dong leaves remains non-empty and connected. The number of zones therefore never changes, and only '
          'dongs on the edge of their zone, the boundary dongs, can move.'),
    ('p', 'The flow-guided path chooses moves by modularity. Modularity, Q, is high when areas in the same zone exchange more trips '
          'with each other than would be expected by chance (Newman, 2006). Within each gu, trips between dongs form a network '
          'that ignores trip direction, with link weights w_ij = f_ij + f_ji and self-loops w_ii = f_ii. At each step, we apply '
          'the move that raises Q the most (resolution 1). For moving dong v from zone a to zone z,'),
    ('eq', 'EQ2'),
    ('pc', 'where k_vz is the weight between v and zone z excluding the self-loop, d is the total link weight of a dong or zone (its '
          'weighted degree) with self-loops counted twice, and m is the total weight in the gu. A gu stops when no move raises Q, '
          'and a dong may be moved more than once. The gu sequences are merged into one citywide sequence by repeatedly taking the '
          'next move with the largest ΔQ across all gu. The path has {nm25} moves in {ngu25} gu in 2025 and {nm20} moves in '
          '{ngu20} gu in 2020. The main analysis applies this rule without limits on zone population or shape; Appendix A reports '
          'a version with both limits.'),
    ('p', 'The random path is the benchmark. It follows the gu order of the flow-guided sequence. At each step it picks, at random, '
          'a dong in that gu that has not yet moved and one of its adjacent zones, and picks again until the move is allowed. We '
          'generated 100 random paths for each year. Both kinds of path are evaluated at every step k, so that flow-guided and '
          'random reassignment are always compared after the same number of moves.'),
    ('h2', '3.3. Alternative maps (Q2)'),
    ('p', 'For the second question, we generated alternative maps with the ReCom chain (DeFord et al., 2021). We ran it separately '
          'in each gu because zones do not cross gu boundaries. Each step merges two adjacent zones, draws a random spanning tree '
          'over the merged area, and cuts it at one link chosen at random among those that give a valid split. A plan is valid if '
          'it has the official number of zones, every zone is connected, each zone’s population (ranked within the gu) is within '
          '±20% of the official zone of the same rank, and the mean Polsby–Popper compactness of the gu’s zones is at least 95% '
          'of the official mean. Polsby–Popper compactness compares a zone’s area with that of a circle with the same perimeter '
          '(Polsby & Popper, 1991). The chains start from the official plan. We discarded the first 500 steps and then kept every '
          '20th map, giving 500 citywide maps from each of two chains per year, or 1000 maps per year. We did not apply a '
          'Metropolis correction, which would reweight the chain so that every valid plan is equally likely. The maps are '
          'therefore not a uniform sample of valid plans; they are a large reference set of alternatives that follow the same size '
          'and shape rules. In four gu the rules allow only one to eight valid plans, and the chains visited all but one of them.'),
    ('p', 'For each map we calculate L and the IFR. We report the share of maps whose L exceeds the official value by more than half '
          'a person, and the effective sample size of each chain, which adjusts the number of maps for the similarity of '
          'successive maps (Geyer, 1992).'),
    ('h2', '3.4. Trips from boundary dongs and the location of facilities (Q3)'),
    ('p', 'The third question is examined for boundary dongs. The unit is a pair (i, z), where i is a boundary dong and z is another '
          'zone in the same gu that contains at least one cell reachable from i within 15 minutes. For each pair we calculate four '
          'shares: W_iz, the share of trips leaving i for other Seoul dongs that end in z; F_iz, the share of the facility cells '
          'within walking distance of i’s residents that lie in z, weighted by the population of the origin cells and averaged '
          'over the seven categories; A_iz, the share of all reachable cells that lie in z; and P_iz, the share of the population '
          'of reachable cells that lives in z. A and P control for differences in how much reachable area and population each '
          'adjacent zone contains. We estimate the partial Spearman correlation between W and F, controlling for A and P. A '
          'second model also controls for the logarithms of zone population and employment. Confidence intervals come from a '
          'bootstrap that resamples dongs (2000 replicates). As a further check, we regress standardised W on F and the controls '
          'with dong fixed effects, so that each dong’s adjacent zones are compared only with each other (1000 replicates). We '
          'also calculate the correlation for each category separately.'),
    ('p', 'The design reported here was chosen after earlier designs had been explored, so all tests should be read as post hoc. '
          'Appendix A lists the analyses that were run but not reported in the main text. The analysis code was written with the '
          'help of a generative AI tool and checked by the authors. Key results were re-run and checked against an independent '
          'implementation.'),
    ('h1', '4. Results'),
    ('h2', '4.1. The official plan'),
    ('p', 'Under the official plan, {L25} residents in 2025 ({L25s}% of the population) and {L20} in 2020 ({L20s}%) could walk to at '
          'least one category of service only outside their own zone (Table 2). Most of this exclusion involves categories with '
          'few facilities: culture ({cul25} residents in 2025) and civic and safety services ({civ25}). Retail and personal '
          'services, whose facilities are dense, add almost nothing (Table A.2). The IFR of the official plan was {ifr25}% in 2025 '
          'and {ifr20}% in 2020.'),
    ('h2', '4.2. Flow-guided versus random reassignment (Q1)'),
    ('p', 'Fig. 2 shows that random reassignment pushed services out. The excluded population rose almost steadily with the number '
          'of dongs moved. After {nm25} moves in 2025, the median random path had added {rm25} excluded residents (middle 95% of '
          'paths: {rlo25} to {rhi25}). After {nm20} moves in 2020 it had added {rm20} ({rlo20} to {rhi20}). All 100 random paths '
          'ended above the official value in both years.'),
    ('fig', 'Fig2'),
    ('p', 'Flow-guided reassignment kept services inside. Its first few moves raised exclusion slightly, but the path then turned '
          'down and stayed below zero. At its lowest point it had reduced exclusion by {fmin25} residents (k = {fk25}) in 2025 and '
          'by {fmin20} (k = {fk20}) in 2020, and it ended at {fe25} and {fe20}. From k = {k25} in 2025 and k = {k20} in 2020 '
          'onwards, the flow-guided path was below all 100 random paths at every step. Before that point some random paths were '
          'lower: at k = 10, for example, {s10_25}% of random paths in 2025 and {s10_20}% in 2020 had less exclusion.'),
    ('p', 'The two kinds of path moved similar numbers of residents. The dongs moved by the flow-guided path held {fp25} residents in '
          '2025, close to the random median of {rp25} (Table 2). The difference lies in the balance of gains and losses. The '
          'flow-guided path newly excluded {fn25} residents and ended exclusion for {fr25}, whereas the median random path newly '
          'excluded {rn25} and ended exclusion for {rr25}. Flow-guided reassignment also raised self-containment: the IFR rose from '
          '{ifr25}% to {fifr25}% in 2025, while random paths lowered it (median {rifr25}%). Following trips therefore improved both '
          'self-containment and within-zone service coverage, while random moves made both worse.'),
    ('p', 'This result holds for the tested modularity rule, with the number of zones fixed and no limits on zone population or '
          'shape. When the population and shape rules of Section 3.3 were applied to every move, the same rule lowered exclusion in '
          '2020 but raised it in 2025, and both paths stopped after 22 moves (Table A.3). The gain therefore depends on the '
          'constraints and on which moves are allowed. We claim it for adjusting an existing plan, not for redesigning zones under '
          'constraints.'),
    ('table', 'T2'),
    ('h2', '4.3. The official plan among alternative maps (Q2)'),
    ('p', 'The official plan excluded fewer residents than {g25} of the 1000 alternative maps in 2025 and {g20} of the 1000 in 2020 '
          '(Fig. 3; Table 3). The median alternative excluded {med25} residents in 2025, {dmed25} more than the official plan, and '
          '{med20} in 2020, {dmed20} more. In 2025, even the best alternative excluded {dmin25} more residents than the official '
          'plan. The official plan also had higher self-containment: {ifr_en} Successive maps in a chain are similar to each '
          'other, and the effective sample size of L ranged from {essmin} to {essmax} per chain. {depend_en}'),
    ('fig', 'Fig3'),
    ('p', 'This does not make the official plan the best possible plan. Among plans that follow the same rules, however, it is unusually good at keeping both walkable services and trips inside its zones.'),
    ('table', 'T3'),
    ('h2', '4.4. Trips from boundary dongs and the location of facilities (Q3)'),
    ('p', 'The analysis covers {np25} dong–zone pairs from {nd25} boundary dongs in 2025 and {np20} pairs from {nd20} dongs in 2020. '
          'After controlling for the shares of reachable area and population, a dong sent a larger share of its trips to an '
          'adjacent zone when a larger share of its walkable facilities was located there (partial ρ = {pc25}, 95% confidence '
          'interval {pc25ci}, in 2025; {pc20}, {pc20ci}, in 2020; Table 4). When zone population and employment were added, the '
          'association remained in 2025 ({pz25}, {pz25ci}), but its interval included zero in 2020 ({pz20}, {pz20ci}). In the '
          'dong fixed-effects model, a facility share one standard deviation higher was associated with a trip share {fe25b} '
          'standard deviations higher in 2025 and {fe20b} in 2020; both bootstrap intervals were above zero.'),
    ('table', 'T4'),
    ('p', 'The association differed by category (Fig. 4). It was strongest for health (ρ = {h25} in 2025 and {h20} in 2020), retail '
          '({r25}, {r20}) and personal services ({s25}, {s20}), and close to zero or negative for education and for childcare and '
          'welfare. Residents usually choose among many nearby clinics, shops and services, whereas schools and childcare centres '
          'often serve assigned or enrolled users; we did not test this explanation. The associations are small, and the '
          'categories that account for most exclusion (culture and civic services) are not those with the strongest association. '
          'What the result establishes is the direction: trips from boundary dongs go towards the adjacent zones that hold more '
          'of their walkable everyday facilities.'),
    ('fig', 'Fig4'),
    ('h1', '5. Discussion and conclusion'),
    ('h2', '5.1. Following trips kept services inside (Q1)'),
    ('p', 'This study started from the concern that moving boundaries towards trips would pull walkable services out of residents’ '
          'zones. In Seoul, the opposite happened. Reassigning boundary dongs by modularity raised the IFR and reduced the number '
          'of residents left outside their zone’s walkable services in both years. From the 15th move in 2025 and the 18th in 2020 '
          'onwards, the flow-guided path stayed below all 100 random paths. Random reassignment of the same extent, moving about as '
          'many residents, pushed services out every time. The difference lies not in how many residents were affected but in the '
          'balance. Both kinds of move newly excluded many residents and ended exclusion for many others, but only the flow-guided '
          'moves ended more exclusion than they created. Section 4.4 points to the reason. Trips from a boundary dong go mostly to '
          'the adjacent zone that already holds more of the clinics, pharmacies, shops and services its residents walk to. A move '
          'that follows the trips therefore brings those facilities inside the boundary. We did not link individual moves to this '
          'association, so this is the reason the evidence points to rather than a tested mechanism. As Section 4.2 showed, the gain holds for the tested rule without limits on zone population or shape.'),
    ('h2', '5.2. The official plan is a sound starting point (Q2)'),
    ('p', 'The official zones left fewer residents outside their zone’s walkable services than almost all alternative maps that '
          'follow the same size and shape rules, and they kept more trips inside than nearly all of them. They were drawn without '
          'mobility data, so this reflects the knowledge that went into them, such as the location of main roads, local centres and '
          'existing facilities. It fits the finding that Seoul’s official zones and mobility communities differ mainly at their '
          'edges (Park et al., 2026). For boundary review, this means that the existing plan should be kept as the starting point '
          'and adjusted at its boundary dongs, and that proposed changes should be judged against it. We did not compare boundary '
          'adjustment with a complete flow-based redesign under the same rules, so the results do not show which approach is '
          'better.'),
    ('h2', '5.3. Trips go where services are (Q3)'),
    ('p', 'Trips from boundary dongs went towards the adjacent zones that held more of their walkable health, retail and '
          'personal-service facilities, but not towards those with more education or childcare facilities. This is the pattern '
          'expected if the first two results share a cause: a dong moved along its trips joins the zone that already holds its '
          'facilities. The association is small and is not strongest in the categories that account for most exclusion, so it '
          'explains the direction of the path results rather than their size. The same pattern should not be assumed elsewhere. '
          'Where most trips are long journeys to regional centres, or where facilities serve assigned catchments, trips and '
          'facilities may point to different places, and flow-guided reassignment could then push services out. What other '
          'cities can take from this paper is the check itself: within-zone coverage can be calculated for any proposed boundary '
          'and compared with a random benchmark of the same extent.'),
    ('h2', '5.4. Implications, limitations and conclusion'),
    ('p', 'Three implications follow. First, mobility data can be used to adjust the boundary dongs of an existing living-zone plan. '
          'In Seoul, this raised self-containment and kept walkable services inside zones, which random adjustment did not. '
          'Second, within-zone service coverage should be checked alongside the IFR for every such revision. The gain is not '
          'automatic: under joint population and shape constraints the same rule lost it in one year, and the random paths show '
          'how quickly coverage falls when moves ignore where residents go. Third, most exclusion involves culture and civic services. Because L counts only '
          'residents who can reach a facility somewhere, high exclusion in these categories shows a mismatch between reachable '
          'supply and zone membership, not a shortage of facilities. The share of residents with no reachable facility at all, '
          'which no boundary can change, is reported separately in Table A.2.'),
    ('p', 'Several limitations apply. Within-zone coverage is a counting measure. It shows which reachable services a plan counts as '
          'residents’ own, not which services they use or how well they are served, and it says nothing directly about welfare. '
          'The analysis covers one city at two dates, each with its own inputs, and comparisons are made within each year. The '
          'results are descriptive, not causal. The alternative maps come from a chain without Metropolis correction and are not a '
          'uniform sample, and in four gu the rules left very few alternatives. In 2020, the dong-level association lost precision once zone size was controlled for. '
          'The mobility data exclude home–work trips, the walking network comes from OpenStreetMap with cell centres matched to '
          'the nearest network point, and 15 minutes is one reasonable threshold among several.'),
    ('p', 'In sum, reassigning the boundary dongs of Seoul’s living-zone plan along observed trips kept walkable services inside the '
          'zones and raised self-containment. Random reassignment of the same extent pushed services out in all 100 simulated '
          'paths, the official plan already did better than almost all comparable alternatives, and trips from boundary dongs went '
          'where their walkable facilities were. The result held in both years with the number of zones fixed and no limits on '
          'zone population or shape. With both limits applied, it held in one year, so it concerns adjusting an existing plan '
          'rather than redesigning zones under constraints. Mobility data can be used to adjust living-zone boundaries, and '
          'within-zone service coverage should be checked whenever they are.'),
]

CAPTIONS = {
    'Fig1': 'Fig. 1. Study area. Seoul’s 25 gu, the 116 official local living zones and the boundary dongs moved by the flow-guided path in '
            '2025. Boundaries: Statistics Korea (dongs, July 2023) and Seoul Metropolitan Government (living zones).',
    'Fig2': 'Fig. 2. Change in the excluded population as boundary dongs are reassigned, relative to the official plan: (a) 2020; (b) 2025. '
            'Thin lines are the 100 random paths, the band shows their middle 95% and the dark blue line their median. The dotted line '
            'marks the step from which the flow-guided path lies below all random paths.',
    'Fig3': 'Fig. 3. Excluded population in 1000 alternative maps per year (two ReCom chains of 500 maps each): (a) 2020; (b) 2025. The '
            'solid line marks the official plan and the dashed line the median alternative.',
    'Fig4': 'Fig. 4. Partial Spearman correlation between the trip share and the walkable facility share of adjacent zones, by facility '
            'category. Controls: reachable area, reachable population, and zone population and employment.',
}
