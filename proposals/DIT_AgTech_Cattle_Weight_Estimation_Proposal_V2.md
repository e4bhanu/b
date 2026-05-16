# DIT AgTech - AI-Powered Cattle Phenotyping Proposal

Internal

PROJECT PROPOSAL

Development of an AI-Powered Camera Vision Method

for Cattle Liveweight Estimation (Cattle phenotyping)

Project Partners

SWINBURNE UNIVERSITY OF TECHNOLOGY

DIT AgTech

Start Date: September 2026 (Research Assistant preparation)

Main Project Start Date: 1 January 2027

End Date: 31 December 2027

Project Duration: 1-2 month preparation phase + 12-month main project

## 1. Project Overview

DIT AgTech is an Australian livestock technology company focused on water-based livestock supplementation and productivity systems. Public company materials describe DIT AgTech as a provider of the uDOSE automated livestock water supplementation system and the uHUB remote monitoring dashboard, enabling producers to deliver supplements through livestock drinking water, monitor usage remotely, improve productivity, and support methane reduction initiatives through products such as uPRO BLUE.

This proposal describes a staged research and development project between Swinburne University of Technology and DIT AgTech to develop an AI-powered camera vision method for estimating the liveweight of beef cattle at drink stations. The proposed capability is a new standalone system that will be designed for future operation within DIT AgTech's AI platform, Nevil.

The project will now begin with an early preparation phase from September 2026. During this phase, a Swinburne research assistant will spend approximately 1-2 months identifying suitable camera options, sensor configurations, mounting positions, capture angles, calibration requirements, and data collection procedures. Swinburne will then provide DIT AgTech with the recommended camera and data collection specification so DIT can acquire the required equipment and begin collecting field data.

The main Swinburne research project will commence on 1 January 2027 and focus on data validation, AI model development, performance evaluation, and prototype handover. The visual data will preferably include RGB plus depth or stereo imagery captured as cattle attend drink stations. Each usable visual observation will be paired with reference liveweight data from the weighing system selected by DIT AgTech.

DIT AgTech has indicated that the liveweight data will be collected using Optiweigh automatic weighing technology. Optiweigh describes its system as a portable, self-contained livestock weighing unit that can be placed in a paddock or feedlot, records animal EID and front-foot weight when cattle step onto the platform, and sends the data to the cloud where algorithms calculate whole-body liveweight. DIT AgTech has advised that the expected liveweight accuracy of this weighing reference is approximately 95-97%. The AI model's accuracy must therefore be interpreted relative to the accuracy and uncertainty of that reference data, not as an absolute measurement beyond the precision of the weighing system itself.

## 2. Expected Outcomes

The project is expected to deliver the following outcomes:

- Research assistant preparation report covering camera options, recommended sensor configuration, mounting position, capture geometry, calibration requirements, and field data collection workflow.
- A data collection specification for DIT AgTech, including recommended RGB/depth or stereo setup, drink-station geometry, trigger logic, metadata fields, and quality acceptance criteria.
- A structured protocol for pairing cattle images or short video snippets with Optiweigh reference liveweight readings.
- A curated training and evaluation dataset assembled from DIT AgTech data batches, with quality labels indicating visibility, occlusion, lighting condition, depth validity, and suitability for model training.
- A trained AI model or model family for beef cattle liveweight estimation from camera vision data captured at drink stations.
- A prototype inference software pipeline that takes camera observations as input and returns estimated liveweight, confidence or uncertainty information, and quality-control flags.
- A performance evaluation report covering model error relative to the Optiweigh liveweight reference, repeatability, subgroup bias, robustness to field conditions, and progress against the agreed target accuracy framework.
- A technical integration specification for future connection to DIT AgTech's Nevil AI platform, including expected inputs, outputs, metadata, confidence thresholds, and suggested API structure.
- A final technical report documenting the method, data assumptions, model architecture, experimental results, limitations, and recommended next development phase.

These outcomes will give DIT AgTech a research-validated foundation for camera-based liveweight estimation and a clear pathway toward productisation if field performance meets the required operational thresholds.

## 3. Technical Objectives

### 3.1 System Architecture - Visual Liveweight Estimation Pipeline

The proposed system is built around supervised learning from paired visual observations and reference liveweight data. Each training example should represent a known animal observation at or near a drink station, with synchronised camera data and a corresponding liveweight record from the Optiweigh system or other confirmed DIT AgTech weighing reference.

### 3.1.1 Preparatory Camera and Capture Design

The September 2026 preparation phase will define the practical field setup before DIT AgTech begins full data collection. The research assistant will review suitable camera technologies and recommend a configuration that balances accuracy, robustness, cost, and ease of installation at drink stations.

The preparation phase will consider:

- RGB, RGB-depth, and stereo camera options.
- Camera mounting height, distance, angle, weather protection, and field of view.
- Whether one or more cameras are needed to capture enough of the animal body.
- Synchronisation between camera capture, animal ID, station events, and weighing-system records.
- Calibration requirements for converting image/depth data into reliable body-size cues.
- Lighting, dust, water reflection, animal crowding, and occlusion risks.
- Practical data storage and transfer requirements for DIT AgTech.

The output of this phase will be a clear data collection guide for DIT AgTech. After receiving this guide, DIT AgTech can install or acquire the required equipment and start collecting paired image/depth and liveweight data before the main January 2027 analysis project begins.

### 3.1.2 Capture Station and Sensor Configuration

The preferred capture configuration is RGB plus depth or stereo camera data. RGB imagery provides visual information about the animal's outline, coat, posture, and body conformation. Depth or stereo information provides approximate three-dimensional shape, camera-to-animal distance, and body size cues. This combination is expected to be more reliable than single RGB images alone, especially where camera distance, animal pose, and station geometry vary.

Swinburne will recommend the camera type, mounting geometry, calibration method, and capture settings. DIT AgTech will acquire and install the required hardware. The recommended setup is expected to include:

- One or more RGB cameras positioned to capture the full side profile or angled side profile of the animal.
- Depth or stereo capability where practical, calibrated to the RGB frame.
- A fixed camera mount with known height, angle, and distance from the expected animal standing position.
- Time synchronisation between camera capture, drinking-station event logs, animal identification if available, and weighing-system records.
- A triggering method based on station activity, animal presence, weight reading, RFID or animal ID event, or computer vision-based detection.

The project will not assume that every captured frame is usable. Field systems should expect occlusion, partial animals, crowding, dirt, water reflections, lighting changes, and off-angle poses. The model pipeline will therefore include quality filtering to reject observations that are unsuitable for reliable weight estimation.

### 3.1.3 Animal Detection, Segmentation, and Quality Gating

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

### 3.1.4 Liveweight Estimation Model

The core model will estimate liveweight using visual and geometric features derived from the RGB and depth/stereo data. Candidate approaches include:

- A convolutional neural network or vision transformer backbone trained on cattle imagery.
- A segmentation-based body-shape pipeline that extracts length, height, area, and volume-related proxies from calibrated images.
- A multimodal regression model combining RGB features, depth-derived size cues, camera geometry, and available metadata such as sex, age class, breed group, or station.
- An uncertainty-aware model that produces an estimated weight plus confidence or prediction interval.

The final architecture will be selected after initial data review and camera testing. The intent is to choose a method that is accurate, explainable enough for field diagnosis, and suitable for future deployment within Nevil.

### 3.1.5 Longitudinal Weight Tracking

Where animal identity is available, repeated measurements over time should be used to improve reliability. Individual estimates can be noisy because of pose, occlusion, camera angle, gut fill, and water intake. A longitudinal model can smooth repeated observations and estimate weight trends, average daily gain, and confidence over time.

The project will support two output modes:

- Single-observation liveweight estimate: estimated weight from one usable camera observation.
- Longitudinal animal-level estimate: smoothed weight estimate derived from repeated observations of the same animal over time.

The second mode is expected to be more valuable for management decisions, provided reliable animal identification is available.

### 3.1.6 Nevil Integration Readiness

The project will produce a prototype inference pipeline and integration specification for DIT AgTech's Nevil AI platform. Full production deployment may require a separate engineering phase depending on DIT AgTech's preferred architecture, security requirements, cloud/edge deployment model, and product roadmap.

The proposed research output will define input formats for image, depth, metadata, and weight records; output schema for estimated liveweight, confidence, quality flags, and model version; recommended thresholds for accepting, flagging, or rejecting predictions; and logging requirements for future monitoring and retraining.

### 3.2 Data Strategy

The success of this project depends primarily on the quality, quantity, and diversity of paired camera and reference liveweight data. DIT AgTech will collect the field data using the agreed capture configuration, while Swinburne will define the data requirements, validate incoming batches, train the AI model, and report performance.

### 3.2.1 Expected Cattle Population and Weight Range

The initial target species and production context is Australian beef cattle across relevant breeds and crossbreeds. Public Australian industry references indicate that mature beef cow weights commonly vary substantially by breed and production system, with mature cow weights often around 550-750 kg, while Meat & Livestock Australia's Heavy Steer Indicator specifies eligible grown steers at 500-600 kg liveweight. Average adult carcase weights are lower than liveweight because they refer to processed carcases rather than live animals.

For system design, Swinburne recommends initially planning for a broad liveweight coverage range of approximately 150-750 kg, subject to confirmation against DIT AgTech's actual target herds. If DIT AgTech expects animals above or below this range, the data collection plan should explicitly include them rather than relying on model extrapolation.

### 3.2.2 Required Data Per Observation

Each training observation should include, where available:

- RGB image or short RGB video snippet.
- Depth map, stereo pair, or calibrated 3D information.
- Reference liveweight from the Optiweigh system.
- Timestamp for image capture.
- Timestamp for weight measurement.
- Animal ID, preferably RFID or another persistent identifier.
- Drink station or site ID.
- Camera ID and calibration version.
- Camera position, mounting height, angle, and distance to expected animal location.
- Breed or breed group, sex, age class, and body condition score if available.
- Weather, lighting, occlusion, crowding, abnormal posture, mud/dust, or poor visibility notes if available.

The image and weight records must be matched accurately. A high-quality dataset with reliable pairing is more valuable than a larger dataset where the wrong animal, wrong time, or wrong weight may be associated with an image.

### 3.2.3 Data Diversity Requirements

The dataset should cover beef cattle across breeds and crossbreeds, different coat colours and body sizes, different body condition scores, horned and polled cattle where relevant, different camera angles, different lighting and weather conditions, clean and dirty animals, and both solo and crowded drink-station events. Multiple properties or stations should be included if DIT AgTech expects deployment across varied environments.

The test set should include animals, sites, and dates not used in training so that evaluation reflects generalisation rather than memorisation of individual animals or locations.

### 3.2.4 Recommended Data Volumes and Batches

Exact data volumes will be finalised after the capture system is designed. As an initial guide:

- Pilot calibration set: 100-200 animals with high-quality paired image/depth and liveweight observations to validate camera geometry and record matching.
- Batch 1 baseline set: 500-1,000 animals, preferably with multiple usable observations per animal, to train and evaluate the first baseline model.
- Batch 2 expansion set: 2,000+ animals across broader conditions, stations, breeds, body sizes, and lighting.
- Batch 3 final set: 3,000+ animals if feasible, with 10-30 usable observations per animal where repeat visits are available.

These figures are not hard minimums, but they reflect the likely scale needed for a robust AI model. If DIT AgTech can collect data from thousands of cattle, the project should use batch-based ingestion so model performance can be tracked as the dataset grows.

### 3.3 Annotation, Quality Assurance, and Dataset Governance

The Optiweigh liveweight record will be treated as the reference label for model training. However, the dataset still requires quality assurance. Swinburne will define rules for accepting or rejecting observations, including:

- Valid liveweight reading present.
- Image and liveweight timestamps are sufficiently close.
- Animal identity is consistent where ID is available.
- Animal body is sufficiently visible.
- Depth or stereo data is usable.
- Camera calibration is current.
- No obvious animal mismatch or multi-animal ambiguity.

DIT AgTech should deliver data in batches using an agreed folder structure and metadata file format. Swinburne will confirm receipt, run validation checks, and report data quality issues so DIT AgTech can adjust collection practices early.

### 3.4 Model Training and Evaluation

The model will be trained using supervised regression, with liveweight as the target output. Evaluation will be conducted on held-out animals and, where possible, held-out drink stations or properties. This is important because randomly splitting images can overstate performance if the same animal appears in both training and test sets.

The following metrics will be tracked:

- Mean absolute error in kilograms, relative to the reference liveweight.
- Root mean squared error in kilograms, relative to the reference liveweight.
- Mean absolute percentage error.
- Percentage of estimates within agreed error bands, such as +/-5%, +/-10%, and agreed kilogram tolerances.
- Bias by weight range, breed group, sex, age class, coat colour, station, and lighting condition where metadata is available.
- Repeatability across multiple observations of the same animal.
- Prediction confidence calibration.
- Rejection rate for low-quality observations.

The model will be developed iteratively. Model accuracy will be reported against the available Optiweigh reference liveweight data, whose expected accuracy has been advised as approximately 95-97%. If independent yard-scale validation data is available, it can be used to separately assess the combined uncertainty of the weighing reference and vision model.

## 4. Scope Boundaries

The project is a research and prototype development project for visual cattle liveweight estimation. The following are in scope:

- Research assistant preparation work to identify camera options, camera position, capture geometry, and data collection requirements.
- Dataset quality framework.
- AI model development and evaluation.
- Prototype inference pipeline.
- Camera placement recommendations.
- Integration specification for Nevil.
- Final technical report and handover.

The following are out of scope unless separately agreed:

- Purchase of production camera hardware by Swinburne.
- Certification of the system as a legal-for-trade weighing device.
- Full production deployment into DIT AgTech infrastructure.
- Long-term cloud operations, cybersecurity hardening, and production monitoring.
- Non-beef species such as sheep, dairy cattle, goats, or pigs.
- Automated animal health diagnosis beyond weight estimation and weight trend reporting.

The appropriate handoff point for this project is a validated method, trained model, prototype software, and integration specification. Productisation can proceed as a follow-on phase once DIT AgTech and Swinburne have reviewed field performance.

## 5. Performance Targets

DIT AgTech has expressed interest in AI-powered cattle weight estimation targeting 95% accuracy. Because this is a research project and the field data has not yet been collected, the proposal treats 95% as an aspirational performance objective rather than a guaranteed commitment at project commencement.

The project will first establish a measurement framework, then set formal numerical targets after Batch 1 data is available and the first baseline model has been evaluated. Targets will be defined relative to the Optiweigh liveweight reference used for training and evaluation. Since DIT AgTech has advised the weighing reference accuracy is approximately 95-97%, the model's measured accuracy should be interpreted within that reference uncertainty.

| Metric | What It Measures | Target Setting |
| --- | --- | --- |
| Mean absolute error (kg) | Average absolute difference between estimated and reference liveweight | Baseline established after Batch 1; final target agreed jointly |
| Root mean squared error (kg) | Sensitivity to large errors | Baseline established after Batch 1; monitored across all batches |
| Mean absolute percentage error | Average percentage error relative to reference liveweight | Candidate metric for interpreting the 95% accuracy ambition |
| Percentage within +/-5% | Share of accepted predictions within 5% of reference liveweight | Aspirational high-confidence target, subject to data quality and reference-weight accuracy |
| Percentage within +/-10% | More tolerant operational accuracy band | Target set after Batch 1 and refined after Batch 2 |
| Bias by subgroup | Whether error changes by breed, coat colour, sex, age class, weight range, or site | Must be reported; mitigation through targeted data collection |
| Low-quality rejection rate | How often the model refuses to produce a high-confidence estimate | Target depends on station design and camera coverage |
| Repeatability | Stability of repeated estimates for the same animal | Evaluated where animal ID and repeated visits are available |
| Longitudinal trend accuracy | Accuracy of weight change over time | Evaluated after repeated observations are available |

Swinburne recommends avoiding correlation alone as the primary metric because a model can have high correlation while still producing biased or commercially unacceptable errors.

## 6. Milestones and Timeline

Preparation Start Date: September 2026

Main Project Start Date: 1 January 2027

End Date: 31 December 2027

Duration: 1-2 month preparation phase + 12-month main project

DIT AgTech data collection is expected to begin after Swinburne delivers the initial camera and capture specification. Data collection should then continue in batches throughout the main project.

### Preparatory Phase - Camera and Data Collection Design (September-October 2026)

Milestone 0 - Camera and Capture Specification Delivered

Due: 31 October 2026

- Research assistant reviews suitable RGB, RGB-depth, and stereo camera options.
- Drink-station camera positions, mounting geometry, and likely field-of-view requirements identified.
- Synchronisation requirements for camera data, animal ID, station event logs, and Optiweigh liveweight records defined.
- Initial calibration and data quality requirements documented.
- Data collection guide delivered to DIT AgTech so DIT can acquire equipment and begin data collection.

### Phase 1 - Main Project Commencement and Data Readiness (Months 1-3)

Milestone 1 - Data Framework and Initial Data Review

Due: 31 March 2027

- Main Swinburne analysis project commences.
- Confirm project objectives, field constraints, and Nevil integration assumptions.
- Review DIT AgTech's collected pilot data and weighing-system workflow.
- Validate image-liveweight pairing, metadata completeness, and visual quality.
- Refine dataset acceptance criteria and quality flags.
- Confirm evaluation metrics and draft target-setting framework.

### Phase 2 - Baseline Model Development (Months 4-6)

Milestone 2 - Baseline Model and Initial Results

Due: 30 June 2027

- Batch 1 data ingested and validated.
- Baseline animal detection, segmentation, and quality-gating pipeline implemented.
- First liveweight estimation model trained using Batch 1 data.
- Initial performance measured using held-out animals.
- Formal numerical performance targets proposed based on empirical results.
- Data gaps identified and fed back to DIT AgTech for Batch 2 collection.

### Phase 3 - Model Improvement, Robustness, and Prototype Integration (Months 7-9)

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
- Accuracy, uncertainty, rejection rate, subgroup bias, and repeatability reported relative to the reference liveweight data.
- Recommended operating thresholds documented.
- Prototype inference software packaged for handover.
- Camera placement and collection recommendations finalised.
- Final technical report delivered.
- Follow-on deployment and productisation pathway documented.

## 7. Risk Management

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Insufficient paired image and liveweight data | Medium | High | Provide camera and data guide before full collection; ingest data in batches; report quality gaps quickly; prioritise high-quality paired observations over raw volume. |
| Reference liveweight accuracy limits model evaluation | Medium | High | Report model accuracy relative to Optiweigh reference data; document the advised 95-97% reference accuracy; use independent yard-scale validation if available. |
| Incorrect matching between images and reference liveweights | Medium | High | Require timestamp synchronisation, animal ID where possible, station event logs, and validation checks for impossible or inconsistent records. |
| Drink-station crowding or occlusion prevents full body visibility | High | High | Use the preparation phase to select camera placement and trigger rules; use quality gating; collect multiple observations per animal; reject low-confidence images. |
| Outdoor lighting, glare, dust, rain, or mud reduces image quality | Medium | Medium | Include environmental diversity in data collection; use image augmentation; specify camera protection and cleaning requirements; monitor quality flags. |
| Depth or stereo sensors perform poorly outdoors | Medium | Medium | Test candidate sensors early; maintain fallback RGB-based baseline; calibrate regularly; compare depth-enabled and RGB-only performance. |
| Model performs differently across breeds, coat colours, body condition, or weight ranges | Medium | High | Collect stratified data across all target breeds and conditions; report subgroup bias; prioritise underrepresented groups in later batches. |
| 95% accuracy target is not supported by field data | Medium | High | Treat 95% as aspirational until Batch 1 baseline; define responsible metrics; set final targets after empirical review; document limitations transparently. |
| Animal ID is unavailable or inconsistent | Medium | Medium | Support single-observation estimation; use event-based matching where possible; treat longitudinal tracking as conditional on reliable ID. |
| Nevil integration requirements change during the project | Medium | Medium | Define integration schema early; keep prototype modular; treat production deployment as a potential follow-on phase if requirements expand. |

## 8. Budget Summary

Indicative Main Project Budget: approximately $252,000, excluding the September-October 2026 research assistant preparation salary.

### Personnel

| Role | 2026 Preparation | 2027 Main Project | Total |
| --- | --- | --- | --- |
| Research Assistant - camera and data collection preparation |  |  |  |
| Researcher - Bhanu Watawana |  | 213,249.57 | 213,249.57 |
| Academic Supervisor - Mats Isaksson |  | 38,726.03 | 38,726.03 |
| Subtotal excluding RA salary |  | 251,975.60 | 251,975.60 |

DIT AgTech's own data collection labour, weighing reference system, drink-station access, and hardware acquisition may be treated as in-kind contribution or direct project cost, depending on the final agreement.

## 9. Project Governance

### Communication and Reporting

- Fortnightly technical meetings between Swinburne and DIT AgTech.
- Data batch review meetings as needed during active collection periods.
- Quarterly milestone reviews aligned with the project phases.
- Written milestone summaries documenting completed work, data received, model performance, risks, and next actions.
- Data handover confirmation after each batch, including quality checks and any required corrective actions.

### Roles and Responsibilities

Swinburne University of Technology will be responsible for:

- Research assistant preparation work on camera options, camera position, and data collection requirements.
- Data requirements and capture specification.
- AI method development.
- Model training and evaluation.
- Prototype inference pipeline.
- Technical reporting and handover.

DIT AgTech will be responsible for:

- Field access and operational context.
- Acquisition and installation of agreed camera hardware.
- Operation of the Optiweigh or other confirmed weighing reference system.
- Collection and transfer of paired image/depth and liveweight data.
- Providing Nevil integration requirements.
- Reviewing milestones and providing domain feedback.

### Intellectual Property and Confidentiality

Intellectual property ownership, commercialisation rights, and publication rights should be confirmed in the formal research agreement before project commencement. Until such agreement is finalised, this proposal assumes that DIT AgTech field data will be treated as confidential and used only for the purposes of this project. Swinburne's right to publish academic findings, if any, should be subject to DIT AgTech review and approval to protect confidential information and commercial interests.

### Data Governance

All field imagery, animal records, and liveweight data should be handled in accordance with Swinburne University of Technology data management requirements and any DIT AgTech confidentiality requirements. Raw data should not be used for purposes outside this project without DIT AgTech's written consent. Any data shared with Swinburne should avoid unnecessary personal or farm-identifying information unless required for the research.

