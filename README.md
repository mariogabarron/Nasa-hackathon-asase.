
<h1 align="center">asase.</h1>

<p align="center">
  <strong>Agricultural intelligence, made accessible.</strong>
</p>

<p align="center">
  From Earth observation data to practical decisions for the communities that need them most.
</p>

<p align="center">
  <a href="https://asase.earth">Explore asase.earth</a>
  ·
  NASA Space Apps Challenge 2026
</p>

---

## 01. Overview

**asase.** is an agricultural decision-support platform designed to help agricultural professionals, engineers, and cooperatives make informed decisions about land use, crop suitability, and crop rotation.

By combining NASA satellite data, soil information, and an interpretable mathematical model, asase. transforms complex environmental information into accessible, actionable agricultural recommendations.

Our first area of focus is **Northern Ghana**, where seasonal rainfall, soil conditions, and limited access to technical resources can make agricultural planning particularly challenging.

**Our mission is simple: make agricultural intelligence accessible to the communities that need it most.**

---

## 02. The Problem

For millions of families, agriculture is more than an economic activity. It is their primary source of food, income, and stability.

Unpredictable rainfall, soil degradation, and limited access to agricultural expertise can turn a single planting decision into a significant economic risk.

While digital agricultural tools continue to emerge, many rely on an assumption: that every farmer has access to a smartphone, reliable internet connectivity, and the technical knowledge required to interpret complex information.

Even in developed countries, solutions designed exclusively for individual farmers can overlook a fundamental challenge: **agricultural problems often extend beyond individual plots and require coordinated decisions at a regional level.**

We believe technology should adapt to communities, not the other way around.

---

## 03. Our Solution

**asase. connects agricultural intelligence with the people who can turn it into action.**

Instead of requiring every farmer to use a digital application, our platform empowers agricultural technicians, engineers, and cooperatives to analyze agricultural conditions, identify vulnerable areas, and communicate recommendations directly to local farmers.

This approach makes it possible to support multiple farmers through a single technical organization.

The platform addresses four essential questions:

- **Where should we act first?** Identify agricultural areas requiring priority attention.
- **What should we plant?** Evaluate crop suitability according to environmental and soil conditions.
- **When should we plant?** Analyze seasonal conditions to support planting decisions.
- **How can we make better use of the land?** Generate crop-rotation strategies to improve land-use planning.

Our goal is not simply to visualize environmental data, but to transform it into useful agricultural decisions.

---

## 04. Platform Features

### Interactive Agricultural Map

Explore agricultural regions through an interactive geographic interface.

The platform allows users to select areas, examine environmental conditions, and visualize information relevant to agricultural planning.

### Crop Suitability Index (IAC)

Evaluate how suitable a particular crop is for a selected location and period.

The **Crop Suitability Index (IAC)** combines environmental and soil parameters using a mathematical weighting system adapted to seasonal conditions and crop requirements.

### Crop Alternatives

Compare different crops according to their suitability for a particular territory.

This allows agricultural professionals to explore alternative planting decisions based on the conditions of the selected area.

### Crop Rotation Recommendations

Generate agricultural rotation strategies across a specified planning period.

The system considers crop cycles, environmental suitability, and planting constraints to produce different recommendations.

Users can request multiple alternatives for comparison.

### Parcel Management

Register crops associated with agricultural parcels and maintain a record of planting activity.

This provides useful context when reviewing land-use decisions and agricultural history.

### Regional Analysis

Analyze agricultural conditions beyond individual parcels.

The platform is designed to support technicians and cooperatives working with multiple agricultural areas and communities.

### Accessible Interface

The web application provides a visual interface designed to make technical agricultural information easier to interpret.

The project includes Spanish and English interface support.

---

## 05. Mathematical Model

At the core of **asase.** is the **Crop Suitability Index (IAC)**, an interpretable mathematical model that evaluates the suitability of a crop under specific environmental and soil conditions.

### Weighted Suitability Model

The IAC uses a weighted multicriteria scoring system:

$$
\mathrm{IAC} = 100 \sum_{i=1}^{n} w_i \cdot s_i
$$

Subject to the normalization constraint:

$$
\sum_{i=1}^{n} w_i = 1
$$

Where:

- $w_i$ represents the weight assigned to environmental parameter $i$.
- $s_i$ represents the suitability score of parameter $i$ for the selected crop.
- $n$ represents the number of active environmental parameters.

Weights vary according to the climatic season, allowing the model to account for changes in the relative importance of environmental factors.

### Suitability Classification

Each parameter is classified using four suitability levels:

| Category | Description | Score |
|----------|-------------|-------|
| S1 | Highly suitable | 1.00 |
| S2 | Moderately suitable | 0.65 |
| S3 | Marginally suitable | 0.30 |
| N | Not suitable | 0.00 |

The model incorporates limiting rules for critical environmental variables.

If a critical parameter is classified as unsuitable, the crop receives a non-suitable classification regardless of its weighted score.

### Seasonal Adaptation

The model considers four climatic periods in Northern Ghana:

1. **Early Rainy Season:** April–June.
2. **Main Rainy Season:** July–September.
3. **Late Rainy Season:** October–November.
4. **Dry Season / Harmattan:** December–March.

The mathematical framework includes 12 crops and crop-specific suitability thresholds.

**Important:** The IAC estimates agricultural suitability. It does not directly predict crop yields, economic returns, or future soil fertility.

---

## 06. Crop Rotation Engine

The crop rotation engine evaluates alternative planting sequences for a selected agricultural area and planning horizon.

Its objectives include:

- Maximizing the proportion of time during which land is cultivated.
- Comparing the suitability of alternative crop sequences.
- Respecting crop growth-cycle constraints.
- Considering seasonal environmental conditions.
- Providing multiple distinct recommendations.

Rotation planning uses historical environmental conditions from 2025 as its climatic reference.

This approach enables the comparison of agricultural scenarios based on historical patterns rather than treating them as guaranteed future weather forecasts.

---

## 07. Data Sources

asase. is built around environmental and soil information from established scientific data providers.

| Source | Data |
|--------|------|
| [NASA POWER](https://power.larc.nasa.gov/) | Historical temperature and solar radiation |
| [NASA GPM](https://gpm.nasa.gov/) | Satellite-based precipitation estimates |
| [NASA SMAP](https://smap.jpl.nasa.gov/) | Soil moisture observations |
| [ISRIC SoilGrids](https://soilgrids.org/) | Estimated soil properties, texture, pH, and organic carbon |

The agricultural model combines these environmental variables with crop-specific agronomic requirements.

The methodology includes seasonal weights, suitability intervals, and limiting conditions for the crops included in the project.

Source coverage and spatial resolution must be considered when interpreting agricultural recommendations.

---

## 08. Technology

The project combines a web application, a Python-based mathematical engine, and an API for agricultural analysis.

### Frontend

- HTML
- CSS
- JavaScript
- Interactive geographic visualization
- Responsive web interface
- Spanish and English language support

### Backend

- Python
- FastAPI
- Mathematical suitability calculations
- Crop-rotation algorithms
- Environmental data processing
- Agricultural recommendation logic

### Main Operations

The calculation engine supports two principal operations:

| Operation | Description |
|-----------|-------------|
| `iac` | Evaluates crop suitability for a selected location and period |
| `rotaciones` | Generates alternative crop-rotation recommendations |

The API is designed to process geographic coordinates, date ranges, crop selection, and planning parameters.

---

## 09. Project Structure

The public repository includes the application and the technical components developed during the project.

```text
space-apps-agriculture/
│
├── API-Predictora-ASASE/
├── ASASE-Integrado/
├── ASASE-Motor-IAC-Rotacion/
├── ASASE-Motor-IAC/
├── api-predictora/
├── aptitud/
├── ideas/
├── justificacion-proyecto/
├── parametros-suelo/
├── python-playground/
├── user-interface/
│
├── cultivo.py
├── cultivo_iac.py
├── territorio.py
├── territorio_iac.py
│
├── README.md
└── LICENSE
```

The repository contains the agricultural model, API implementations, interface development, experimental code, and methodological documentation.

**Repository:** [github.com/mariogabarron/space-apps-agriculture](https://github.com/mariogabarron/space-apps-agriculture)

---

## 10. Our Team

asase. was developed by a multidisciplinary team combining software development, mathematical modeling, data analysis, and user experience design.

| Area | Team Members |
|------|--------------|
| User Interface & Experience | Clara & Mario |
| Data Sources & Processing | Albero & Edu |
| Mathematical Model & Python Algorithms | Navarro & David |

Developed in the context of the **NASA Space Apps Challenge 2026**.

---

## 11. Our Vision

We believe that living in a low-resource community should never determine someone's opportunities.

Agricultural knowledge, environmental information, and technological progress should be accessible beyond the most developed regions of the world.

Our approach is designed to make this possible by empowering the agricultural professionals and cooperatives who already work directly with farming communities.

Northern Ghana is our starting point, but our vision extends much further.

By adapting agricultural parameters, expanding regional coverage, and incorporating additional environmental information, asase. aims to support agricultural decision-making in more communities around the world.

**Our ultimate goal is not simply to improve crops. It is to help more families find new opportunities to prosper from their land.**

---

## 12. Responsible Use

asase. is an agricultural decision-support tool.

Its recommendations depend on environmental data quality, model assumptions, and the representativeness of available soil information.

Agricultural suitability estimates should be interpreted alongside local expertise, field measurements, and the practical conditions faced by farmers.

The system is intended to support informed agricultural decisions rather than replace professional agronomic judgment.

---

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE) for details.

---

### asase.

**Intelligence for the land. Opportunity for the people.**

🌍 [asase.earth](https://asase.earth)
