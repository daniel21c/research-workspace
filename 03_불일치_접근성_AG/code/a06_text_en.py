# -*- coding: utf-8 -*-
"""영문 원고 본문(Applied Geography 형식). 숫자는 모두 {키}로 두고 a06_manuscript.py가 결과 파일에서 채운다.
블록: ('h1'|'h2', 제목), ('p', 문단), ('eq', 수식 한 줄), ('table', 표 키), ('fig', 그림 키).
"""

TITLE = 'Following trips, keeping services? Mobility-guided revision of neighbourhood planning zones and within-zone walkable service coverage in Seoul'

ABSTRACT = (
    'Cities that plan by neighbourhood zones are increasingly asked to redraw them with mobility data, on the assumption that a zone holding more of its residents’ trips is a better planning unit. A zone, however, is also the unit through which everyday services are counted and promised to residents, and a boundary that follows trips may leave walkable facilities on the wrong side of the line. We examine this tension in Seoul’s living-zone plan, combining mobile-phone origin–destination flows, a geocoded inventory of everyday facilities and a walking network at two points in time. We count the residents who can walk to a category of service only by leaving their own zone. Reassigning boundary neighbourhoods at random increased this number; the same number of flow-guided reassignments, with zone counts fixed and no population or compactness bounds, reduced it to below every simulated random path. Among alternative zone maps matched to the official plan in size and compactness, the official zones excluded fewer residents than almost all sampled alternatives. Trips from boundary neighbourhoods leaned towards adjacent zones holding more of their walkable facilities. In Seoul, then, following trips did not come at the cost of services: revising zones along observed flows kept walkable facilities inside them, because trips and facilities pointed to the same places. Flow-guided adjustment of an existing plan is a usable tool, provided within-zone coverage is checked alongside flow containment; under joint population and shape constraints the gain held in one year only.')

KEYWORDS = ['Neighbourhood planning', 'Functional regions', 'Walking accessibility', 'Boundary revision', 'Redistricting ensembles', 'Mobility data', 'Seoul']

HIGHLIGHTS = [
    'Random reassignment of boundary dongs ended with more residents excluded',
    'Flow-guided reassignment ended with fewer, without population or shape bounds',
    'Seoul’s zones exclude fewer residents than nearly all sampled matched alternatives',
    'Trips from boundary dongs lean towards neighbouring zones with more services',
    'Following trips kept walkable services inside Seoul’s zones; random moves did not',
]

BODY = [
    ('h1', '1. Introduction'),
    ('p', 'Planning by neighbourhood has returned to the centre of urban policy. The 15-minute city, the 20-minute neighbourhood '
          'and a family of related schemes ask that the places people need in daily life be reachable on foot from home (Moreno '
          'et al., 2021; Allam et al., 2022; Logan et al., 2022). Behind these slogans sits an older and more practical device '
          'that we call here a living zone: a territory, smaller than a municipality and larger than a block, within which a '
          'bundle of everyday services is planned, counted and eventually delivered. Its lineage runs from Perry’s (1929) '
          'neighbourhood unit, sized by the walking catchment of an elementary school and furnished with shops, open space and '
          'community facilities, to the neighbourhood planning guidelines reviewed by Park and Rogers (2015), and to Talen’s '
          '(2003) treatment of neighbourhoods as service providers whose walkable supply can be measured.'),
    ('p', 'Cities use territorial units for planning and monitoring at different scales. Berlin’s lifeworld-oriented spaces '
          'provide a spatial reference for social planning and demographic monitoring (Berlin Senate Department for Urban '
          'Development, Building and Housing, 2021). The 2016 London Plan used sub-regions for statutory monitoring and '
          'cross-borough coordination (Greater London Authority, 2016), and Greater Sydney’s 2018 strategy organised three cities '
          'and five districts around a thirty-minute access aspiration (Greater Sydney Commission, 2018). These units differ in '
          'scale and institutional function. Seoul’s living-zone plan, adopted as part of the city’s 2030 planning framework, '
          'comprises five regional and 116 local living zones and uses the local zones to diagnose service shortfalls and set '
          'local priorities (Seoul Metropolitan Government, 2018). These examples illustrate territorial planning at several '
          'scales, not a common guarantee of everyday services within each boundary; it is the local living zone, with its '
          'service-diagnosis role, that this paper examines.'),
    ('p', 'Most such zones were drawn from administrative boundaries, local knowledge and negotiation rather than from data on '
          'how residents move. Now that large mobility datasets are routinely available, a new question is being put to such '
          'plans: do the official zones match the territories that people’s trips actually form? Studies of Seoul and of other '
          'cities have found that they often do not, and that communities detected in origin–destination networks cut across '
          'official lines (Shen & Batty, 2019; Park et al., 2026). The obvious response is to move boundaries towards the flows. '
          'It follows a long tradition in functional regionalisation, where a region is judged good if it contains most of the '
          'interaction that starts in it (Smart, 1974; Coombes et al., 1986; Karlsson & Olsson, 2006).'),
    ('p', 'That response carries a difficulty that has received little attention. A planning zone is not only a container of '
          'trips; it is also an accounting unit. When a city plans by zone, the facilities located inside a zone are counted as '
          'serving its residents, and a resident whose reachable clinics or libraries all lie just across the line appears, in '
          'the zone’s accounts, to lack that service. Moving a boundary to capture more trips can therefore push walkable '
          'facilities out of residents’ zones even though nothing on the ground has changed. If this happens widely, a revision '
          'that looks better by the standard of self-containment will look worse by the standard the plan was created to serve. '
          'Accessibility research has mostly treated boundaries as a source of measurement error to be minimised (Fotheringham & '
          'Wong, 1991; Kwan, 2012; Gao et al., 2017), not as planning objects whose revision changes which services residents are '
          'deemed to have.'),
    ('p', 'This paper examines that trade-off directly. We ask whether, when mobility data are used to revise living-zone '
          'boundaries, the facilities that residents can walk to remain inside their zones. We study Seoul’s 116 official zones '
          'and the 424 administrative neighbourhoods (dongs) from which they are built, in 2020 and 2025, combining a '
          'mobile-phone origin–destination matrix, an inventory of everyday facilities assembled from public registers, and a '
          'walking network. Within-zone service coverage is measured by the number of residents who can reach a category of '
          'service within a 15-minute walk only by leaving their own zone. Three questions are examined (Q1–Q3 below). First, '
          'does reassigning boundary dongs along observed trips raise or lower that number, compared with the same number of '
          'random reassignments? Second, how does the official plan compare with a large set of alternative maps that obey the '
          'same size and shape rules, generated with the ensemble methods developed for electoral redistricting (DeFord et al., '
          '2021)? Third, do trips from boundary dongs go towards the neighbouring zones that hold more of the facilities their '
          'residents can walk to?'),
    ('p', 'At the end of the main paths, without population or compactness bounds, the answers agree in both years: random '
          'reassignment increased the number of residents without within-zone coverage, whereas the same number of flow-guided '
          'reassignments reduced it. The official zones exclude fewer residents than nearly every alternative map. And trips from '
          'boundary dongs lean towards the neighbouring zones where walkable facilities are, a pattern consistent with the first '
          'two results. In Seoul, then, following trips did not come at the cost of services. The paper makes two contributions. '
          'It treats within-zone service coverage as a property of a boundary, distinct from accessibility as such, and shows how '
          'it can be measured with standard inputs. It also evaluates boundary revisions against explicit baselines rather than '
          'in isolation, borrowing the logic of plan ensembles from redistricting. Section 2 reviews the literature behind the '
          'boundary problem (2.1) and each question (2.2–2.4); Sections 3, 4 and 5 treat methods, results and discussion in the '
          'same order, with implications and limitations in Section 5.4.'),
    ('h1', '2. Literature review'),
    ('h2', '2.1. Living zones as service units and the boundary problem'),
    ('p', 'Proximity-based planning has renewed interest in such units. Work on the 15-minute city measures whether residents can '
          'reach a range of amenity categories within a fixed walking time (Weng et al., 2019; Moreno et al., 2021; Logan et al., '
          '2022; Staricco, 2022), and increasingly how this varies between people and over the day (Willberg et al., 2023). '
          'Critics note that proximity targets say little about capacity, quality or who benefits (Mouratidis, 2024). Most of '
          'these measurements radiate from the home and ignore planning boundaries. That is sensible when the question is whether '
          'a resident can reach a service. It sets aside a different question, one that matters to planners who work by zone: '
          'whether the service a resident can reach is one the plan counts as theirs.'),
    ('p', 'Public finance and the literature on territorial justice give that question weight. The principle of fiscal '
          'equivalence holds that the territory over which a service is provided should match the population that benefits from '
          'it (Olson, 1969), and territorial justice asks whether services are distributed across areas in proportion to their '
          'needs (Boyne & Powell, 1991). Both take areas to be the units through which services are allocated and judged. Seoul’s '
          'living-zone plan works in the same way: facility shortfalls are diagnosed zone by zone, and each zone plan sets '
          'priorities for what should be provided within it (Seoul Metropolitan Government, 2018). A zone, in this sense, is a '
          'promise that a set of everyday services will be found inside it. Whether a boundary keeps that promise is a property '
          'of the boundary, and not only of the facilities. We use this reading as an accounting convention for the analysis; it '
          'does not claim that the plan guarantees every category within each zone, or that residents are restricted from using '
          'services across boundaries.'),
    ('p', 'Accessibility has been measured in many ways since Hansen (1959), from cumulative opportunities to gravity and '
          'utility-based measures (Handy & Niemeier, 1997; Geurs & van Wee, 2004; Páez et al., 2012), and it is a standard tool '
          'for assessing spatial equity in service provision (Talen & Anselin, 1998). Boundaries appear in this literature mainly '
          'as a problem. Results change with the zoning used for aggregation (Openshaw, 1984; Fotheringham & Wong, 1991), the '
          'geographic context attributed to a person is uncertain (Kwan, 2012), aggregating demand to zone centroids distorts '
          'distances (Hillsman & Rhoda, 1978), and supply beyond the edge of a study area is easily missed (Gao et al., 2017). '
          'Tao et al. (2018) showed that restricting healthcare supply to residents’ own administrative units changes measured '
          'accessibility considerably, and argued that the restriction reflects how services are actually organised there.'),
    ('p', 'We take this last point further. When a plan allocates services by zone, the gap between what residents can reach and '
          'what they can reach within their zone is not an artefact to be corrected; it is exactly what the zone boundary '
          'decides. We call the extent to which reachable services fall inside the resident’s own zone within-zone service '
          'coverage, and the residents for whom some reachable category lies wholly outside their zone the excluded population.'),
    ('h2', '2.2. Functional regions and flow-based revision of boundaries'),
    ('p', 'The main alternative to drawing zones by administrative convenience is to derive them from interaction. Functional '
          'regionalisation groups areas so that most flows starting in a region also end there. Smart (1974) and Coombes et al. '
          '(1986) set out the self-containment criteria that still underlie British travel-to-work areas (Coombes & Bond, 2008), '
          'and Karlsson and Olsson (2006) reviewed the theory and methods more broadly. Later work recast the task as a network '
          'problem. Farmer and Fotheringham (2011) treated functional regions as communities in a flow network, Ratti et al. '
          '(2010) redrew the map of Great Britain from telecommunication links, and Halás et al. (2015) and Klapka et al. (2020) '
          'refined rule-based and graph-based procedures. Community detection by modularity (Newman, 2006) and its refinements '
          '(Traag et al., 2019) has become a standard tool, although the treatment of self-loops (He et al., 2020) and the '
          'suitability of standard modularity for spatial interaction data (Martínez-Bernabéu & Casado-Díaz, 2021) remain under '
          'discussion.'),
    ('p', 'The same methods have been applied to service areas. Wang et al. (2021) delineated hospital service areas by detecting '
          'communities in patient flows under spatial constraints, and Shen and Batty (2019) derived the perceived functional '
          'regions of London from commuting. In Seoul, Park et al. (2026) benchmarked the official living-zone plan against '
          'communities detected in mobile-phone mobility networks and found that the two partitions diverge in systematic ways. '
          'What this literature evaluates, however, is the fit between a partition and its flows; a flow-based region is judged '
          'by how much of its own interaction it holds. What happens to the services a planning zone is expected to contain when '
          'its boundary moves along the flows has not, to our knowledge, been examined, and no study compares such a flow-guided '
          'revision with revisions of the same extent made without flow information. That comparison is our first question.'),
    ('h2', '2.3. Judging a plan against its alternatives'),
    ('p', 'A single plan’s coverage value says little by itself. The redistricting literature faced the same problem and '
          'addressed it by comparing an enacted plan with large ensembles of alternative plans that satisfy the same rules. Chen '
          'and Rodden (2013) used simulated plans to separate the effects of political geography from those of deliberate design, '
          'Herschlag et al. (2020) used Markov chain sampling to evaluate North Carolina’s districts, and DeFord et al. (2021) '
          'introduced the recombination (ReCom) chain, which proposes new plans by merging two adjacent districts and splitting '
          'them along a random spanning tree. Territory design in operations research deals with similar partitioning problems '
          'under balance and compactness requirements (Kalcsics et al., 2005), and zone design in geography has long explored how '
          'many alternative zonings a set of rules allows (Openshaw & Rao, 1995). We borrow two ideas from this work. A revision '
          'should be judged against revisions of the same extent made without the information that guided it, which shapes the '
          'random baseline of Section 3.2; and a plan should be judged against the plans it could have been, which is our second '
          'question.'),
    ('h2', '2.4. Trips and the location of everyday services'),
    ('p', 'The third question asks whether trips and walkable facilities tend to point to the same places. Accessibility has long '
          'been related to the location of activity (Hansen, 1959). Alexander et al. (2015) inferred trips by broad purpose and '
          'time of day from mobile-phone data, distinguishing home-based work, home-based other and non-home-based trips. In '
          'Barcelona, Graells-Garrido et al. (2021) found that visits were associated with greater destination accessibility to '
          'education and retail, with local variation in sign and magnitude. These studies motivate examining the spatial '
          'association between trips and reachable services, but do not imply that mobility-guided boundary changes reduce '
          'exclusion. If trips tend to go where services are, a boundary drawn around trips may keep services inside zones rather '
          'than push them out; whether this holds at the boundaries of an existing plan, and for which services, has not been '
          'examined.'),
    ('h2', '2.5. Gaps and research questions'),
    ('p', 'Three gaps follow from this review: flow-based revision is judged by containment alone, a single plan’s coverage is '
          'rarely judged against the plans it could have been, and the spatial relation between trips and walkable services at '
          'plan boundaries is untested. Three questions address them. RQ1: does reassigning boundary dongs along observed trips '
          'change the population excluded from within-zone walkable services, compared with the same number of random '
          'reassignments? RQ2: where does the official plan sit among alternative maps that satisfy the same size and shape '
          'rules? RQ3: do trips from boundary dongs go towards the neighbouring zones that hold more of the facilities their '
          'residents can walk to? RQ3 gives descriptive context for RQ1: a positive association would be consistent with partial '
          'co-location of trips and facilities, but would not by itself imply that the reassignment rule reduces exclusion.'),
    ('h1', '3. Data and methods'),
    ('h2', '3.1. Study area, data and indicators'),
    ('p', 'Seoul’s 2024 population grid counts {pop25m} million residents in 25 autonomous districts (gu) and 424 dongs. The '
          'living-zone plan groups the dongs into 116 local living zones, each lying within a single gu (Fig. 1). We use a '
          'version of the plan in which each dong is assigned to the zone it overlaps most, with dong boundaries held at their '
          'July 2023 form in both years, so that plans differ only in the assignment of dongs to zones. Table 1 summarises the '
          'data.'),
    ('fig', 'Fig1'),
    ('p', 'Mobility is represented by origin–destination flows between dongs from Seoul’s living-mobility data, which the city '
          'estimates from mobile-phone signals. We use January 2020 and January 2025, all days of the week and trips arriving '
          'between 09:00 and 20:59, and remove trips between home and workplace so that the flows describe daytime activity other '
          'than commuting. Cells suppressed for privacy are set to zero, and only flows with both ends in Seoul are kept. Trips '
          'that begin and end in the same dong are included. The resulting matrices hold {od20m} million trips in 2020 and '
          '{od25m} million in 2025.'),
    ('p', 'Residents are represented by the 100 m population grid of Statistics Korea for 2019 and 2024. Facilities come from an '
          'inventory we assembled from national and municipal registers, including business licensing records, education, '
          'welfare, health and culture registers, and lists of public offices. It covers 27 facility types in seven categories: '
          'education, childcare and welfare, health, culture, civic and safety services, retail, and personal services (Appendix '
          'Table A1). Each facility is located to a 100 m cell and dated as close to the end of 2019 and of 2024 as its source '
          'allows. Sports businesses were excluded because their records could not be harmonised between the two years. The '
          'analysis uses {fac20} facility records in 2020 and {fac25} in 2025, occupying {cell20} and {cell25} cells.'),
    ('p', 'Walking times are computed on OpenStreetMap extracts dated 1 January 2020 and 1 January 2025, clipped to Seoul with a '
          '2 km buffer. Ways usable on foot were kept, the network was treated as undirected, and a walking speed of 4 km/h was '
          'assumed. The time between two cells is the shortest network time between the nodes nearest to their centroids, and a '
          'cell counts as reachable from another if this time is 15 minutes or less.'),
    ('table', 'T1'),
    ('p', 'Within each year the flows, population, facilities and network are fixed, and only the assignment of dongs to zones '
          'changes. Differences between 2020 and 2025 mix changes in every input, so we do not read them as trends. The second '
          'year serves to check whether the same pattern appears under a different set of inputs.'),
    ('p', 'Two indicators are computed for every plan. Let o index populated 100 m cells with population p_o, let c index the '
          'seven facility categories, and let b be a plan that assigns each dong, and hence each cell, to a zone. Let r_oc = 1 if '
          'a cell containing a facility of category c can be reached from o within 15 minutes, and r_oc^b = 1 if such a cell can '
          'be reached and lies in the same zone as o under plan b. The walking route may pass through other zones; only the '
          'location of the destination matters. The population of cell o is excluded under b if at least one category is '
          'reachable but not within the zone:'),
    ('eq', 'EQ1'),
    ('p', 'Each resident is counted once, however many categories are affected. A category that a resident cannot reach at all '
          'does not count towards L, since that is a lack of access no boundary can repair; such a resident may still enter L '
          'through another category. L therefore measures how much of the walkable supply a plan places outside residents’ zones. '
          'For a revised plan b relative to the official plan b_0, the change ΔL = N − R separates residents newly excluded (N) '
          'from those whose exclusion is resolved (R). The separation matters because large gains and losses can cancel.'),
    ('p', 'We also report the internal flow ratio, the share of trips between Seoul dongs that begin and end in the same zone:'),
    ('eq', 'EQ3'),
    ('pc', 'where f_ij is the number of trips from dong i to dong j. L is an accounting quantity. It records which reachable '
          'services a plan counts as lying inside a resident’s zone, not which services residents use or whether they are '
          'prevented from using those outside.'),
    ('h2', '3.2. Flow-guided and random reassignment of boundary dongs (Q1)'),
    ('p', 'The first question is answered by comparing two kinds of reassignment path. A reassignment moves one dong to an '
          'adjacent zone in the same gu, where two dongs are adjacent if their polygons touch (queen contiguity). A move is '
          'allowed only if the zone the dong leaves stays non-empty and contiguous, so the number of zones never changes and only '
          'dongs on the edge of their zone can move.'),
    ('p', 'The flow-guided revision chooses moves by modularity. Within each gu, trips between dongs form an undirected weighted '
          'network with w_ij = f_ij + f_ji and self-loops w_ii = f_ii. At each step the move that most increases modularity Q '
          '(resolution 1; Newman, 2006) is applied. For moving dong v from zone a to zone z,'),
    ('eq', 'EQ2'),
    ('pc', 'where k_vz is the weight between v and zone z excluding the self-loop, d is the weighted degree with self-loops '
          'counted twice, and m is the total weight in the gu. A gu stops when no move raises Q, and a dong may be moved more '
          'than once. The district sequences are merged into one citywide sequence by repeatedly taking, among the gu, the next '
          'move with the largest ΔQ. The resulting path has {nm25} moves in {ngu25} gu in 2025 and {nm20} moves in {ngu20} gu in '
          '2020. The main analysis evaluates this modularity rule with no population or compactness bounds; Appendix A reports a '
          'version with both constraints applied.'),
    ('p', 'The random revision is the baseline. It follows the gu order of the flow-guided sequence; at each step it draws, '
          'uniformly at random, a dong in that gu that has not yet moved and one of its adjacent zones, redrawing until the move '
          'is allowed. One hundred random paths were generated for each year. Both kinds of path are evaluated at every step k, '
          'so that flow-guided and random revisions are always compared after the same number of moves.'),
    ('h2', '3.3. Alternative maps (Q2)'),
    ('p', 'For the second question we generated alternative maps with the ReCom chain (DeFord et al., 2021), run separately in '
          'each gu because zones do not cross gu boundaries. Each proposal merges two adjacent zones, draws a uniform spanning '
          'tree over the merged area and cuts one of its edges, chosen at random among those that yield a valid split. A plan is '
          'valid if it has the official number of zones, every zone is contiguous, each of the gu’s sorted zone populations is '
          'within ±20% of the official zone of the same rank, and the mean Polsby–Popper compactness of the gu’s zones (Polsby & '
          'Popper, 1991) is at least 95% of the official mean. The chains start from the official plan. We discarded the first '
          '500 proposals and kept every 20th state thereafter, obtaining 500 citywide maps from each of two chains per year, '
          '1,000 maps per year in all. No Metropolis correction was applied, so the maps are not a uniform sample of valid plans; '
          'they are best read as a large reference set of alternatives that obey the same size and shape rules. In four gu the '
          'rules admit very few partitions. Exhaustive enumeration found between one and eight valid partitions there, and the '
          'chains visited all of them except one alternative in one gu in 2020.'),
    ('p', 'For each map we compute L and IFR and report the share of maps whose L exceeds the official value by more than half a '
          'person, together with the effective sample size of each chain (Geyer, 1992).'),
    ('h2', '3.4. Trips from boundary dongs and the location of facilities (Q3)'),
    ('p', 'The third question is examined at the level of boundary dongs. The analysis examines whether trips from boundary dongs '
          'are associated with where their reachable facilities lie among neighbouring zones; it does not estimate the mechanism '
          'behind the changes in exclusion along the reassignment paths. The unit is a pair (i, z), where i is a boundary dong '
          'and z is a zone in the same gu, other than i’s own, that contains at least one cell reachable from i within 15 '
          'minutes. For each pair we compute W_iz, the share of trips leaving i for other Seoul dongs that end in z; F_iz, the '
          'share of the facility cells reachable on foot from i’s residents that lie in z, weighted by origin-cell population and '
          'averaged over the seven categories; A_iz, the share of all reachable cells that lie in z; and P_iz, the share of the '
          'population of reachable cells that lives in z. A and P adjust for measured differences in the shares of reachable area '
          'and population across neighbouring zones. We estimate the partial Spearman correlation between W and F controlling for '
          'A and P, and in a second specification also for the logarithms of zone population and employment. Confidence intervals '
          'come from a bootstrap that resamples dongs (2,000 replicates). As a further check we regress standardised W on F and '
          'the controls with dong fixed effects, so that each dong’s neighbouring zones are compared only with one another (1,000 '
          'replicates). The correlation is also computed for each category separately.'),
    ('p', 'The specification reported here was settled after earlier designs had been explored, so all tests should be read as '
          'post hoc. Appendix A lists the analyses that were run but not carried into the main text. Analysis code was written '
          'with the assistance of a generative AI tool and reviewed by the authors; key results were re-run and cross-checked '
          'against an independent implementation of the evaluation.'),
    ('h1', '4. Results'),
    ('h2', '4.1. The official plan'),
    ('p', 'Under the official plan, {L25} residents in 2025 ({L25s}% of the population) and {L20} in 2020 ({L20s}%) could walk to '
          'at least one category of service only outside their own zone (Table 2). Most of this exclusion concerns categories '
          'with sparse facilities: culture ({cul25} residents in 2025) and civic and safety services ({civ25}). Retail and '
          'personal services, whose facilities are dense, contribute almost nothing (Appendix Table A2). The IFR of the official '
          'plan was {ifr25}% in 2025 and {ifr20}% in 2020.'),
    ('h2', '4.2. Flow-guided versus random reassignment (Q1)'),
    ('p', 'Random reassignment raised the excluded population almost linearly with the number of dongs moved (Fig. 2). After '
          '{nm25} moves in 2025 the median random path had added {rm25} excluded residents (central 95% of paths, {rlo25} to '
          '{rhi25}); after {nm20} moves in 2020 it had added {rm20} ({rlo20} to {rhi20}), and every random path ended above the '
          'official value.'),
    ('fig', 'Fig2'),
    ('p', 'The flow-guided path behaved differently. Its first few moves raised exclusion slightly, after which it turned down '
          'and stayed below zero. At its lowest it had reduced exclusion by {fmin25} residents (k = {fk25}) in 2025 and by '
          '{fmin20} (k = {fk20}) in 2020, and it ended at {fe25} and {fe20}. From k = {k25} in 2025 and k = {k20} in 2020 '
          'onwards, the flow-guided path lay below every one of the 100 random paths at every step. Before that point some random '
          'paths were lower; at k = 10, for example, {s10_25}% of random paths in 2025 and {s10_20}% in 2020 had less exclusion.'),
    ('p', 'The endpoint comparison involved similar totals of residents in the reassigned dongs: the dongs moved by the '
          'flow-guided path held {fp25} residents in 2025, close to the random median of {rp25} (Table 2). What differs is the '
          'balance of gains and losses. The flow-guided path newly excluded {fn25} residents and resolved exclusion for {fr25}, '
          'whereas the median random path newly excluded {rn25} and resolved {rr25}. The flow-guided path also raised the IFR, '
          'from {ifr25}% to {fifr25}% in 2025, while random paths lowered it (median {rifr25}%). At the end of the path, '
          'following flows had raised self-containment and lowered aggregate exclusion, although large numbers of residents '
          'entered and left the excluded group along the way; random moves lost on both counts.'),
    ('p', 'This result concerns the tested modularity rule with the number of zones fixed and no population or compactness '
          'bounds. When the population and compactness rules of Section 3.3 were applied jointly to each move, the same rule '
          'lowered exclusion in 2020 but raised it in 2025, and both paths ended after 22 moves (Appendix Table A3). The result '
          'is therefore sensitive to the constraints and to the set of feasible moves; it is not an isolated effect of population '
          'balance and should not be extended to constrained redesign.'),
    ('table', 'T2'),
    ('h2', '4.3. The official plan among alternative maps (Q2)'),
    ('p', 'The official plan excluded fewer residents than {g25} of the 1,000 alternative maps in 2025 and {g20} of the 1,000 in '
          '2020 (Fig. 3, Table 3). The median alternative excluded {med25} residents in 2025, {dmed25} more than the official '
          'plan, and {med20} in 2020, {dmed20} more. In 2025 even the best alternative excluded {dmin25} more residents than the '
          'official plan. The official plan also led on IFR: {ifr_en} Successive maps in a chain are correlated, and the '
          'effective sample sizes of L ranged from {essmin} to {essmax} per chain. {depend_en}'),
    ('fig', 'Fig3'),
    ('p', 'These results do not show that the official plan is optimal, and they do not rest on a uniform sample. They show that '
          'among many plans obeying the same size and shape rules, the official one keeps walkable services inside zones '
          'unusually well, and that it does so while also containing more trips.'),
    ('table', 'T3'),
    ('h2', '4.4. Trips from boundary dongs and the location of facilities (Q3)'),
    ('p', 'The analysis covers {np25} dong–zone pairs from {nd25} boundary dongs in 2025 and {np20} pairs from {nd20} dongs in '
          '2020. Controlling for the shares of reachable area and population, the share of a dong’s trips going to a neighbouring '
          'zone rose with the share of its walkable facilities located there (partial ρ = {pc25}, 95% CI {pc25ci}, in 2025; '
          '{pc20}, {pc20ci}, in 2020; Table 4). When zone population and employment were added, the association remained in 2025 '
          '({pz25}, {pz25ci}), but its interval included zero in 2020 ({pz20}, {pz20ci}). In the dong fixed-effects model, a '
          'facility share one standard deviation higher went with a trip share {fe25b} standard deviations higher in 2025 and '
          '{fe20b} in 2020, both with bootstrap intervals above zero.'),
    ('table', 'T4'),
    ('p', 'The association differed by category (Fig. 4). It was strongest for health (ρ = {h25} in 2025 and {h20} in 2020), '
          'retail ({r25}, {r20}) and personal services ({s25}, {s20}). It was close to zero or negative for education and for '
          'childcare and welfare. One reading, not tested here, is that residents choose among many nearby providers in the '
          'former categories whereas the latter serve assigned or enrolled users. The associations are modest. They are '
          'consistent with partial co-location of trips and walkable facilities, but they do not establish the mechanism behind '
          'the changes in exclusion reported in Section 4.2, and the categories that account for most exclusion (culture, civic '
          'services) are not those where the association is strongest.'),
    ('fig', 'Fig4'),
    ('h1', '5. Discussion and conclusion'),
    ('h2', '5.1. Following trips and aggregate service coverage (Q1)'),
    ('p', 'The concern that motivated this study was that redrawing zones around trips might pull walkable services out of '
          'residents’ zones. In Seoul, for the tested rule with no population or compactness bounds, the opposite happened. '
          'Flow-guided reassignment reduced the excluded population in aggregate, while the same number of random reassignments, '
          'moving about as many people, increased it. The dong-level analysis offers a plausible, though not demonstrated, '
          'interpretation: trips from a boundary dong go disproportionately to the neighbouring zone that holds more of the '
          'clinics, pharmacies, shops and services its residents can walk to, and a move into that zone brings those facilities '
          'inside the boundary. What the paths do show is that moves of both kinds newly excluded and resolved large numbers of '
          'residents, and that the balance was favourable only along the flow-guided path.'),
    ('h2', '5.2. The official plan among its alternatives (Q2)'),
    ('p', 'The official zones placed fewer residents outside their zone’s walkable services than almost all sampled alternative '
          'maps obeying the same size and shape rules. They were drawn without mobility data, so this presumably reflects the '
          'knowledge that went into them, such as the location of main roads, local centres and existing facilities. It is '
          'consistent with evidence that official plans and mobility communities in Seoul differ mainly at their edges (Park et '
          'al., 2026). For revision, it means that the existing plan is a sound starting point against which proposed changes can '
          'be judged. We did not compare boundary adjustment with a flow-guided redesign of whole zones under the same rules, so '
          'the results do not show that one approach is preferable to the other.'),
    ('h2', '5.3. Trips, facilities and the limits of a co-location reading (Q3)'),
    ('p', 'Trips from boundary dongs went towards the neighbouring zones that held more of their walkable health, retail and '
          'personal-service facilities, and not towards those holding more education or childcare facilities. This is the pattern '
          'one would expect if the first two results share a cause: a dong moved along its trips joins the zone that already '
          'holds its facilities. We did not test that link, the association is modest, and it is not strongest in the categories '
          'that account for most exclusion, so the co-location is offered as the likely reason rather than a demonstrated one. '
          'This co-location should not be assumed elsewhere. Different mobility patterns and service systems, such as trips '
          'dominated by long journeys to regional centres or facilities with assigned catchments, may produce different '
          'associations, but the category-specific associations observed here do not determine the direction of exclusion changes '
          'elsewhere. The transferable part of the paper is therefore less the Seoul result than the check itself: within-zone '
          'coverage can be computed for any proposed boundary and compared with a random baseline of the same extent.'),
    ('h2', '5.4. Implications, limitations and conclusion'),
    ('p', 'Three implications follow. First, flow data can be used to adjust the boundary dongs of an existing plan: in Seoul '
          'this kept walkable services inside zones while raising self-containment, which random adjustment did not. Second, the '
          'check on within-zone coverage should travel with every such revision, because the gain is not automatic: under joint '
          'population and shape constraints the same rule lost it in one year, and the random paths show how quickly coverage is '
          'lost when moves ignore where residents go. Once reachability inputs exist, the measure can be computed for any '
          'proposed assignment. Third, most exclusion concerns culture and civic services. Because L counts only residents who '
          'can reach a facility somewhere, high exclusion in these categories indicates a mismatch between reachable supply and '
          'zone membership; it does not by itself show that provision is insufficient. The share of residents with no reachable '
          'facility at all, which no boundary can change, is reported separately in Appendix Table A2.'),
    ('p', 'Several limitations qualify these conclusions. Within-zone coverage is an accounting concept: it indicates which '
          'reachable services a plan counts as residents’ own, not which services they use or how well they are served, and the '
          'results say nothing directly about welfare. The analysis covers one city at two dates, each with its own inputs, and '
          'comparisons are made within each year; they are descriptive, not causal. The alternative maps come from a chain '
          'without Metropolis correction and are not a uniform sample, and in four gu the rules left very few alternatives. As '
          'Section 4.2 showed, the main result is specific to the tested rule and constraints. In 2020 the dong-level association '
          'lost precision once zone size was controlled. The mobility data exclude home–work trips, the network is '
          'OpenStreetMap-based with centroids snapped to nodes, and 15 minutes is one plausible threshold.'),
    ('p', 'In sum, revising Seoul’s living-zone boundaries along observed trips kept walkable services inside the zones. Random '
          'revisions of the same length pushed them out in every one of 100 simulated paths, the official plan already '
          'outperformed almost all comparable alternatives, and trips from boundary neighbourhoods went where their walkable '
          'facilities were. The result held in both years for the tested rule, with the number of zones fixed and no population '
          'or compactness bounds; with those constraints applied jointly it held in one year, so it concerns the adjustment of an '
          'existing plan rather than constrained redesign. Mobility data can be used to adjust living-zone boundaries, and '
          'within-zone service coverage should be checked whenever they are.'),
]

CAPTIONS = {
    'Fig1': 'Fig. 1. Study area: Seoul’s 25 gu, the 116 official local living zones and the dongs moved by the flow-guided revision in 2025.',
    'Fig2': 'Fig. 2. Change in the excluded population as boundary dongs are reassigned, relative to the official plan. Thin lines are the 100 '
            'random paths; the band is their central 95% and the dark line their median. The dotted line marks the step from which the '
            'flow-guided path lies below all random paths.',
    'Fig3': 'Fig. 3. Excluded population in 1,000 alternative maps per year (two ReCom chains of 500 maps). The solid line marks the official '
            'plan and the dashed line the median alternative.',
    'Fig4': 'Fig. 4. Partial Spearman correlation between the share of a boundary dong’s trips going to a neighbouring zone and the share of '
            'its walkable facilities of each category located there, controlling for reachable area, reachable population and zone '
            'population and employment.',
}
