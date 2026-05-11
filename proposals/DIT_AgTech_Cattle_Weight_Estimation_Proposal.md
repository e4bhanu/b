# DIT AgTech - AI-Powered Cattle Liveweight Estimation Proposal v1

PROJECT PROPOSAL

Development of an AI-Powered Camera Vision Method for Cattle Liveweight Estimation at Drink Stations

Project Partners

SWINBURNE UNIVERSITY OF TECHNOLOGY

DIT AgTech

Swinburne Researcher: Bhanu Watawana

Academic Supervisor: Mats Isaksson

DIT AgTech Contact: Prasan Ghimire, Software Lead

Start Date: 1 January 2027

End Date: 31 December 2027

Project Duration: 12 Months

Indicative Total Budget: approximately $259,000

Version: v1

## 1. Project Overview

DIT AgTech is an Australian livestock technology company focused on water-based livestock supplementation and productivity systems. Public company materials describe DIT AgTech as a provider of the uDOSE automated livestock water supplementation system and the uHUB remote monitoring dashboard, enabling producers to deliver supplements through livestock drinking water, monitor usage remotely, improve productivity, and support methane reduction initiatives through products such as uPRO BLUE.

This proposal describes a 12-month research and development project between Swinburne University of Technology and DIT AgTech to develop an AI-powered camera vision method for estimating the liveweight of beef cattle at drink stations. The proposed capability is a new standalone system that will be designed for future operation within DIT AgTech's AI platform, Nevil. The project will use camera imagery, preferably RGB plus depth or stereo data, captured as cattle attend drinking stations. Each usable visual observation will be paired with ground-truth liveweight from DIT AgTech's existing weighing system.

The motivation is straightforward: liveweight is one of the most important indicators for livestock productivity, health, supplementation effectiveness, market readiness, and management decision-making. Conventional weighing is accurate, but it can be labour-intensive, episodic, and dependent on dedicated animal handling infrastructure. Drink stations create a repeatable opportunity for passive observation because animals visit them naturally and frequently. If visual liveweight estimation can be made reliable, DIT AgTech can add a valuable AI layer to its productivity platform: weight estimates and weight-change trends generated from routine animal behaviour.

The project will proceed in two linked stages. First, Swinburne will define the data, hardware geometry, calibration, metadata, and quality requirements DIT AgTech needs to collect. DIT AgTech will then acquire the required camera hardware and collect paired image/depth and weighing-system data. Once sufficient data is available, Swinburne will train and evaluate AI models that estimate cattle liveweight from visual information and produce a prototype inference pipeline suitable for future Nevil integration.

The project will treat the requested 95% accuracy objective as an aspirational target rather than a fixed guarantee at proposal stage. The final achievable performance depends on data volume, quality, animal visibility, weight range, breed and coat diversity, camera placement, lighting, depth quality, and the precision of matching images to ground-truth weights. A formal performance target will therefore be set after the first substantial data batch has been reviewed and a baseline model has been trained.

## 2. Expected Outcomes

The project is expected to deliver the following outcomes:

- A detailed data collection and camera placement specification for DIT AgTech, including recommended RGB/depth or stereo setup, station geometry, calibration process, trigger logic, metadata fields, and quality acceptance criteria.
- A structured data protocol for pairing cattle images or short video snippets with ground-truth liveweight readings from DIT AgTech's existing weighing system.
- A curated training and evaluation dataset assembled from DIT AgTech data batches, with quality labels indicating visibility, occlusion, lighting condition, depth validity, and suitability for model training.
- A trained AI model or model family for beef cattle liveweight estimation from camera vision data captured at drink stations.
- A prototype inference software pipeline that takes camera observations as input and returns estimated liveweight, confidence or uncertainty information, and quality-control flags.
- A performance evaluation report covering mean error, percentage error, repeatability, subgroup bias, robustness to field conditions, and progress against the agreed target accuracy framework.
- A technical integration specification for future connection to DIT AgTech's Nevil AI platform, including expected inputs, outputs, metadata, confidence thresholds, and suggested API structure.
- Camera placement and operating recommendations for future deployment, including guidance on image quality, animal positioning, sensor calibration, and minimum acceptable visibility.
- A final technical report documenting the method, data assumptions, model architecture, experimental results, limitations, and recommended next development phase.

These outcomes will give DIT AgTech a research-validated foundation for camera-based liveweight estimation and a clear pathway toward productisation if field performance meets the required operational thresholds.

## 3. Technical Objectives

### 3.1 System Architecture - Visual Liveweight Estimation Pipeline

The proposed system is built around supervised learning from paired visual observations and ground-truth liveweight data. Each training example should represent a known animal observation at or near a drink station, with synchronised camera data and a corresponding weight reading from the existing DIT AgTech weighing system.

#### 3.1.1 Capture Station and Sensor Configuration

The preferred capture configuration is RGB plus depth or stereo camera data. RGB imagery provides visual information about the animal's outline, coat, posture, and body conformation. Depth or stereo information provides approximate three-dimensional shape, camera-to-animal distance, and body size cues. This combination is expected to be more reliable than single RGB images alone, especially where camera distance, animal pose, and station geometry vary.

Swinburne will recommend the camera type, mounting geometry, calibration method, and capture settings. DIT AgTech will acquire and install the required hardware. The recommended setup is expected to include:

- One or more RGB cameras positioned to capture the full side profile or angled side profile of the animal.
- Depth or stereo capability where practical, calibrated to the RGB frame.
- A fixed camera mount with known height, angle, and distance from the expected animal standing position.
- Time synchronisation between camera capture, drinking-station event logs, animal identification if available, and weighing-system records.
- A triggering method based on station activity, animal presence, weight reading, RFID or animal ID event, or computer vision-based detection.

The project will not assume that every captured frame is usable. Field systems should expect occlusion, partial animals, crowding, dirt, water reflections, lighting changes, and off-angle poses. The model pipeline will therefore include quality filtering to reject observations that are unsuitable for reliable weight estimation.

#### 3.1.2 Animal Detection, Segmentation, and Quality Gating

Before estimating weight, the system must identify the animal in the image and determine whether enough of the body is visible. A detection and segmentation stage will locate the animal, separate it from the background, and estimate whether the body is sufficiently complete for downstream regression.

Quality-control flags may include:

- Full or partial body visible.
- Side profile, angled profile, front/rear view, or unclear pose.
- Occlusion from another animal, station structure, trough, fence, or shadow.
- Depth map completeness.
- Motion blur.
- Lighting condition.
- Camera obstruction, dust, rain, mud, or water splash.

Only observations that meet the agreed quality threshold will be used for high-confidence weight estimation. Lower-quality observations may still be stored for later improvement, but they should not be treated as reliable production estimates unless validated.

#### 3.1.3 Liveweight Estimation Model

The core model will estimate liveweight using visual and geometric features derived from the RGB and depth/stereo data. Candidate approaches include:

- A convolutional neural network or vision transformer backbone trained on cattle imagery.
- A segmentation-based body-shape pipeline that extracts length, height, area, and volume-related proxies from calibrated images.
- A multimodal regression model combining RGB features, depth-derived size cues, camera geometry, and available metadata such as sex, age class, breed group, or station.
- An uncertainty-aware model that produces an estimated weight plus confidence or prediction interval.

The final architecture will be selected after initial data review and camera testing. The intent is not to over-engineer the first version, but to choose a method that is accurate, explainable enough for field diagnosis, and suitable for future deployment within Nevil.

#### 3.1.4 Longitudinal Weight Tracking

Where animal identity is available, repeated measurements over time should be used to improve reliability. Individual estimates can be noisy because of pose, occlusion, camera angle, gut fill, and water intake. A longitudinal model can smooth repeated observations and estimate weight trends, average daily gain, and confidence over time.

The project will therefore support two output modes:

- Single-observation liveweight estimate: estimated weight from one usable camera observation.
- Longitudinal animal-level estimate: smoothed weight estimate derived from repeated observations of the same animal over time.

The second mode is expected to be more valuable for management decisions, provided reliable animal identification is available.

#### 3.1.5 Nevil Integration Readiness

The project will produce a prototype inference pipeline and integration specification for DIT AgTech's Nevil AI platform. Full production deployment may require a separate engineering phase depending on DIT AgTech's preferred architecture, security requirements, cloud/edge deployment model, and product roadmap.

The proposed research output will define:

- Input formats for image, depth, metadata, and weight records.
- Output schema for estimated liveweight, confidence, quality flags, and model version.
- Recommended thresholds for accepting, flagging, or rejecting predictions.
- Logging requirements for future model monitoring and retraining.
- Versioning expectations for models and datasets.

### 3.2 Data Strategy

The success of this project depends primarily on the quality, quantity, and diversity of paired camera and ground-truth weight data. DIT AgTech will collect the field data using the agreed capture configuration, while Swinburne will define the data requirements, validate incoming batches, train the AI model, and report performance.

#### 3.2.1 Expected Cattle Population and Weight Range

The initial target species and production context is Australian beef cattle across all relevant breeds and crossbreeds. Public Australian industry references indicate that mature beef cow weights commonly vary substantially by breed and production system, with mature cow weights often around 550-750 kg, while Meat & Livestock Australia's Heavy Steer Indicator specifies eligible grown steers at 500-600 kg liveweight. Average adult carcase weights are lower than liveweight because they refer to processed carcases rather than live animals.

For system design, Swinburne recommends initially planning for a broad liveweight coverage range of approximately 150-750 kg, subject to confirmation against DIT AgTech's actual target herds. This range allows for younger animals, yearlings, heifers, cows, and grown steers. If DIT AgTech expects animals above or below this range, the data collection plan should explicitly include them rather than relying on model extrapolation.

#### 3.2.2 Required Data Per Observation

Each training observation should include, where available:

- RGB image or short RGB video snippet.
- Depth map, stereo pair, or calibrated 3D information.
- Ground-truth liveweight from the existing weighing system.
- Timestamp for image capture.
- Timestamp for weight measurement.
- Animal ID, preferably RFID or another persistent identifier.
- Drink station or site ID.
- Camera ID and calibration version.
- Camera position, mounting height, angle, and distance to expected animal location.
- Breed or breed group, if known.
- Sex and age class, if known.
- Body condition score, if available.
- Weather and lighting condition, if available.
- Notes on occlusion, crowding, abnormal posture, mud/dust, or poor visibility.

The image and weight records must be matched accurately. A high-quality dataset with reliable pairing is more valuable than a larger dataset where the wrong animal, wrong time, or wrong weight may be associated with an image.

#### 3.2.3 Data Diversity Requirements

The dataset should cover the range of conditions under which DIT AgTech expects the system to operate:

- Beef cattle across breeds and crossbreeds.
- Different coat colours and patterns, including dark, light, red, grey, brindle, and mixed coats.
- Different body sizes, growth stages, and body condition scores.
- Horned and polled cattle where relevant.
- Different camera angles and small variations in animal position.
- Morning, midday, afternoon, dusk, and artificial-light conditions where relevant.
- Sunny, overcast, wet, dusty, muddy, and high-glare conditions.
- Clean and dirty animals.
- Solo animals and crowded drink-station events.
- Multiple properties or stations if DIT AgTech expects deployment across varied environments.

The test set should include animals, sites, and dates not used in training so that evaluation reflects generalisation rather than memorisation of individual animals or locations.

#### 3.2.4 Recommended Data Volumes and Batches

Exact data volumes will be finalised after the capture system is designed. As an initial guide:

- Pilot calibration set: 100-200 animals with high-quality paired image/depth and weight observations to validate camera geometry and record matching.
- Batch 1 baseline set: 500-1,000 animals, preferably with multiple usable observations per animal, to train and evaluate the first baseline model.
- Batch 2 expansion set: 2,000+ animals across broader conditions, stations, breeds, body sizes, and lighting.
- Batch 3 final set: 3,000+ animals if feasible, with 10-30 usable observations per animal where repeat visits are available.

These figures are not hard minimums, but they reflect the likely scale needed for a robust AI model. If DIT AgTech can collect data from thousands of cattle, the project should use batch-based ingestion so model performance can be tracked as the dataset grows.

### 3.3 Annotation, Quality Assurance, and Dataset Governance

Unlike object detection projects that require extensive manual labelling, this project can use the weighing system as the primary ground-truth label source. However, the dataset still requires quality assurance. Swinburne will define rules for accepting or rejecting observations, including:

- Valid weight reading present.
- Image and weight timestamps are sufficiently close.
- Animal identity is consistent where ID is available.
- Animal body is sufficiently visible.
- Depth or stereo data is usable.
- Camera calibration is current.
- No obvious animal mismatch or multi-animal ambiguity.

DIT AgTech should deliver data in batches using an agreed folder structure and metadata file format. Swinburne will confirm receipt, run validation checks, and report data quality issues so DIT AgTech can adjust collection practices early.

### 3.4 Model Training and Evaluation

The model will be trained using supervised regression, with liveweight as the target output. Evaluation will be conducted on held-out animals and, where possible, held-out drink stations or properties. This is important because randomly splitting images can overstate performance if the same animal appears in both training and test sets.

The following metrics will be tracked:

- Mean absolute error in kilograms.
- Root mean squared error in kilograms.
- Mean absolute percentage error.
- Percentage of estimates within agreed error bands, such as +/-5%, +/-10%, and agreed kilogram tolerances.
- Bias by weight range, breed group, sex, age class, coat colour, station, and lighting condition where metadata is available.
- Repeatability across multiple observations of the same animal.
- Prediction confidence calibration.
- Rejection rate for low-quality observations.

The model will be developed iteratively. Each new data batch should improve either the model's accuracy, robustness, coverage, or confidence calibration. If performance does not improve, the evaluation will identify whether the limiting factor is data volume, data quality, camera placement, animal pose, ground-truth timing, or model design.

## 4. Scope Boundaries

The project is a research and prototype development project for visual cattle liveweight estimation. The following are in scope:

- Data and camera capture specification.
- Dataset quality framework.
- AI model development and evaluation.
- Prototype inference pipeline.
- Camera placement recommendations.
- Integration specification for Nevil.
- Final technical report and handover.

The following are out of scope unless separately agreed:

- Purchase of production camera hardware by Swinburne.
- Physical construction or modification of drink stations.
- Certification of the system as a legal-for-trade weighing device.
- Replacement of DIT AgTech's existing weighing system during the research phase.
- Full production deployment into DIT AgTech infrastructure.
- Long-term cloud operations, cybersecurity hardening, and production monitoring.
- Non-beef species such as sheep, dairy cattle, goats, or pigs.
- Automated animal health diagnosis beyond weight estimation and weight trend reporting.

The appropriate handoff point for this project is a validated method, trained model, prototype software, and integration specification. Productisation can proceed as a follow-on phase once DIT AgTech and Swinburne have reviewed field performance.

## 5. Performance Targets

DIT AgTech has expressed interest in AI-powered cattle weight estimation targeting 95% accuracy. Because this is a research project and the data does not yet exist in validated form, the proposal treats 95% as an aspirational performance objective rather than a guaranteed commitment at project commencement.

The project will first establish a measurement framework, then set formal numerical targets after Batch 1 data is available and the first baseline model has been evaluated. This avoids overpromising before the team understands animal visibility, drink-station geometry, data matching quality, and liveweight distribution.

| Metric | What It Measures | Target Setting |
| --- | --- | --- |
| Mean absolute error (kg) | Average absolute difference between estimated and ground-truth liveweight | Baseline established after Batch 1; final target agreed jointly |
| Root mean squared error (kg) | Sensitivity to large errors | Baseline established after Batch 1; monitored across all batches |
| Mean absolute percentage error | Average percentage error relative to actual weight | Candidate metric for interpreting the 95% accuracy ambition |
| Percentage within +/-5% | Share of accepted predictions within 5% of scale weight | Treated as an aspirational high-confidence target, subject to data quality |
| Percentage within +/-10% | More tolerant operational accuracy band | Target set after Batch 1 and refined after Batch 2 |
| Bias by subgroup | Whether error changes by breed, coat colour, sex, age class, weight range, or site | Must be reported; mitigation through targeted data collection |
| Low-quality rejection rate | How often the model refuses to produce a high-confidence estimate | Target depends on station design and camera coverage |
| Repeatability | Stability of repeated estimates for the same animal | Evaluated where animal ID and repeated visits are available |
| Longitudinal trend accuracy | Accuracy of weight change over time | Evaluated after repeated observations are available |

The preferred interpretation of the 95% ambition will be agreed during the project. Candidate definitions include mean absolute percentage error below 5%, 95% of accepted predictions falling within an agreed error band, or correlation above 0.95. Swinburne recommends avoiding correlation alone as the primary metric because a model can have high correlation while still producing biased or commercially unacceptable errors.

## 6. Milestones and Timeline

Start Date: 1 January 2027

End Date: 31 December 2027

Duration: 12 Months

DIT AgTech data collection is expected to begin after Swinburne delivers the initial data and capture specification. Data collection should then continue in batches throughout the project.

### Phase 1 - Foundation, Capture Design, and Data Specification (Months 1-2)

Milestone 1 - Data and System Framework Established

Due: 28 February 2027

- Confirm project objectives, field constraints, and Nevil integration assumptions.
- Review existing DIT AgTech weighing system and expected drink-station workflow.
- Define camera hardware requirements and recommended RGB/depth or stereo configuration.
- Define mounting geometry, calibration process, trigger logic, and time synchronisation requirements.
- Produce data collection guide and metadata schema for DIT AgTech.
- Define dataset acceptance criteria and quality flags.
- Confirm initial evaluation metrics and draft target-setting framework.

### Phase 2 - Pilot Collection and Baseline Model (Months 3-5)

Milestone 2 - Pilot Dataset and Baseline Results

Due: 31 May 2027

- DIT AgTech collects pilot and Batch 1 data according to the agreed specification.
- Swinburne validates image-weight pairing, metadata completeness, and visual quality.
- Baseline animal detection, segmentation, and quality-gating pipeline implemented.
- First liveweight estimation model trained using Batch 1 data.
- Initial performance measured using held-out animals.
- Formal numerical performance targets proposed based on empirical results.
- Data gaps identified and fed back to DIT AgTech for Batch 2 collection.

### Phase 3 - Model Improvement, Robustness, and Prototype Integration (Months 6-9)

Milestone 3 - Improved Model and Nevil-Ready Prototype Specification

Due: 30 September 2027

- Batch 2 data ingested, validated, and incorporated into training.
- Model improved using expanded diversity across animals, stations, lighting, and weight ranges.
- Depth/stereo features and camera calibration refinements incorporated where available.
- Uncertainty and confidence scoring implemented.
- Longitudinal smoothing explored where animal ID and repeated visits are available.
- Bias analysis completed across available subgroups.
- Prototype inference pipeline prepared with defined input/output schema.
- Draft Nevil integration specification delivered to DIT AgTech.

### Phase 4 - Final Validation and Handover (Months 10-12)

Milestone 4 - Final Deliverables

Due: 31 December 2027

- Final data batch ingested and validated.
- Final model trained and evaluated on held-out animals and, where possible, held-out stations or dates.
- Accuracy, uncertainty, rejection rate, subgroup bias, and repeatability reported.
- Recommended operating thresholds documented.
- Prototype inference software packaged for handover.
- Camera placement and collection recommendations finalised.
- Final technical report delivered.
- Follow-on deployment and productisation pathway documented.

## 7. Risk Management

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Insufficient paired image and weight data | Medium | High | Provide detailed data guide early; ingest data in batches; report quality gaps quickly; prioritise high-quality paired observations over raw volume. |
| Incorrect matching between images and ground-truth weights | Medium | High | Require timestamp synchronisation, animal ID where possible, station event logs, and validation checks for impossible or inconsistent records. |
| Drink-station crowding or occlusion prevents full body visibility | High | High | Recommend camera placement and trigger rules; use quality gating; collect multiple observations per animal; reject low-confidence images. |
| Outdoor lighting, glare, dust, rain, or mud reduces image quality | Medium | Medium | Include environmental diversity in data collection; use image augmentation; specify camera protection and cleaning requirements; monitor quality flags. |
| Depth or stereo sensors perform poorly outdoors | Medium | Medium | Test candidate sensors early; maintain fallback RGB-based baseline; calibrate regularly; compare depth-enabled and RGB-only performance. |
| Model performs differently across breeds, coat colours, body condition, or weight ranges | Medium | High | Collect stratified data across all target breeds and conditions; report subgroup bias; prioritise underrepresented groups in later batches. |
| 95% accuracy target is not supported by field data | Medium | High | Treat 95% as aspirational until Batch 1 baseline; define responsible metrics; set final targets after empirical review; document limitations transparently. |
| Animal ID is unavailable or inconsistent | Medium | Medium | Support single-observation estimation; use event-based matching where possible; treat longitudinal tracking as conditional on reliable ID. |
| Nevil integration requirements change during the project | Medium | Medium | Define integration schema early; keep prototype modular; treat production deployment as a potential follow-on phase if requirements expand. |

## 8. Budget Summary

Indicative Total Project Budget: approximately $259,000.

Detailed budget allocation will be completed manually by Swinburne and DIT AgTech. The following structure is provided for consistency with the template proposal.

### Personnel

| Role | 2027 | Total |
| --- | --- | --- |
| Researcher - Bhanu Watawana | To be completed | To be completed |
| Academic Supervisor - Mats Isaksson | To be completed | To be completed |
| Additional research, technical, or administrative support | To be completed | To be completed |

### Operational and Equipment Costs

| Category | 2027 | Total |
| --- | --- | --- |
| Camera and depth/stereo hardware | To be completed by DIT AgTech / Swinburne | To be completed |
| Compute, storage, and data management | To be completed | To be completed |
| Travel, site visits, and field validation | To be completed | To be completed |
| Consumables and miscellaneous costs | To be completed | To be completed |

DIT AgTech's own data collection labour, existing weighing system, drink-station access, and hardware acquisition may be treated as in-kind contribution or direct project cost, depending on the final agreement.

## 9. Project Governance

### Communication and Reporting

- Fortnightly technical meetings between Swinburne and DIT AgTech.
- Data batch review meetings as needed during active collection periods.
- Quarterly milestone reviews aligned with the four project phases.
- Written milestone summaries documenting completed work, data received, model performance, risks, and next actions.
- Data handover confirmation after each batch, including quality checks and any required corrective actions.

### Roles and Responsibilities

Swinburne University of Technology will be responsible for:

- Data requirements and capture specification.
- AI method development.
- Model training and evaluation.
- Prototype inference pipeline.
- Technical reporting and handover.

DIT AgTech will be responsible for:

- Field access and operational context.
- Acquisition and installation of agreed camera hardware.
- Operation of the existing weighing system.
- Collection and transfer of paired image/depth and weight data.
- Providing Nevil integration requirements.
- Reviewing milestones and providing domain feedback.

### Intellectual Property and Confidentiality

Intellectual property ownership, commercialisation rights, and publication rights should be confirmed in the formal research agreement before project commencement. Until such agreement is finalised, this proposal assumes that DIT AgTech field data will be treated as confidential and used only for the purposes of this project. Swinburne's right to publish academic findings, if any, should be subject to DIT AgTech review and approval to protect confidential information and commercial interests.

### Data Governance

All field imagery, animal records, and weight data should be handled in accordance with Swinburne University of Technology data management requirements and any DIT AgTech confidentiality requirements. Raw data should not be used for purposes outside this project without DIT AgTech's written consent. Any data shared with Swinburne should avoid unnecessary personal or farm-identifying information unless required for the research.

## 10. Preliminary Data Collection Guidance

The following guidance will be refined during Phase 1 and issued as a formal data collection protocol.

### Minimum Data Capture Requirements

- Capture each animal with a clear view of the body, preferably side-on or angled side-on.
- Record a valid scale weight as close as possible in time to the image capture.
- Record animal ID whenever possible.
- Store raw RGB images and raw depth/stereo data rather than compressed screenshots.
- Record camera calibration and mounting details.
- Keep all timestamps in a consistent time zone and format.
- Preserve failed, rejected, or low-quality examples separately rather than deleting them immediately, because they help diagnose field failure modes.

### Recommended Metadata Fields

- Observation ID.
- Animal ID.
- Station ID.
- Camera ID.
- Timestamp of image capture.
- Timestamp of weight reading.
- Ground-truth liveweight.
- Breed or breed group.
- Sex.
- Age class.
- Body condition score if available.
- Weather and lighting condition.
- Camera calibration version.
- Image quality notes.

### Initial Acceptance Criteria for Training Images

- Animal visible from shoulder to rump.
- At least one usable side or angled-side view.
- Limited occlusion from other animals or station infrastructure.
- Weight reading confidently linked to the same animal.
- Depth/stereo data aligned with RGB image where used.
- No severe motion blur or camera obstruction.

## 11. Public Sources Reviewed

The proposal uses public company and industry context from:

- DIT AgTech public website materials on livestock water supplementation, uDOSE, uHUB, and uPRO BLUE.
- DIT AgTech public "About" and automated livestock dosing system pages.
- Meat & Livestock Australia Heavy Steer Market Indicator information sheet, specifying 500-600 kg liveweight for eligible grown steers.
- Meat & Livestock Australia industry commentary on adult cattle carcase weights, used only as contextual background and not as a substitute for liveweight ground truth.

