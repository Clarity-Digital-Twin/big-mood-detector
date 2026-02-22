# 🍎 **Apple Health Data Export Guide**

> Using Fitbit instead of Apple Health? See [Fitbit Export Guide](FITBIT_EXPORT.md).

## **📱 Two Export Methods Available**

### **Method 1: Official Apple Health Export (XML)**
```
iPhone → Health App → Profile → Export All Health Data → ZIP file
```

**What you get:**
- `export.xml` - Raw sensor data (every heartbeat, step, sleep stage)
- File size: 2GB+ for active users
- Contains complete historical data
- **Used by**: Apple Health Bot for general health Q&A

**Security:** 
- ⚠️ **NEVER commit to git** - contains personal health information
- Store in `apple_export/` directory (gitignored)

### **Method 2: Third-Party JSON Export (Current Setup)**
```
"Health Auto Export - JSON+CSV" app → Daily aggregated JSON files
```

**What you get:**
- Daily summary files: `Sleep Analysis.json`, `Active Energy.json`, etc.
- Processed aggregated data perfect for mood analysis
- Manageable file sizes (KB instead of GB)
- **Used by**: Big Mood Detector for mood pattern analysis

---

## **🏗️ Dual Pipeline Architecture**

```
Personal Health Data Sources:
├── export.xml           # → Apple Health Bot (general health Q&A)
└── data/*.json          # → Big Mood Detector (mood analysis)
```

For current Big Mood Detector CLI usage, place Apple XML at:

- `data/input/apple_export/export.xml`

and run:

```bash
big-mood process data/input/apple_export/export.xml
big-mood predict data/input/apple_export/export.xml --report --output data/output/clinical_report_apple.txt
```

### **Apple Health Bot Pipeline (XML)**
```python
# Raw XML processing for comprehensive health analysis
python dataParser/xmldataparser.py export.xml
```

### **Big Mood Detector Pipeline (JSON)**
```python
# Aggregated JSON processing for mood detection
from big_mood_detector.infrastructure.parsers.json import SleepParser
parser = SleepParser()
sleep_records = parser.parse("data/Sleep Analysis.json")
```

---

## **🔒 Security & Privacy**

### **Personal Data Protection**
```gitignore
# NEVER commit personal health data
apple_export/
personal_data/
health_exports/
*.zip
*.xml
export.xml
export_*.xml
*.sqlite
```

### **Safe Development Practice**
1. **Local only**: Keep health exports in gitignored directories
2. **Test data**: Use synthetic/anonymized data for tests
3. **Environment separation**: Separate personal vs. research data
4. **Documentation**: This file documents the dual approach

---

## **🎯 Implementation Status**

### **✅ Completed**
- JSON parser infrastructure for mood analysis
- Security configurations for personal data
- Dual pipeline architecture design

### **🔄 In Progress**
- XML parser integration with Apple Health Bot
- Cross-pipeline data validation
- Synthetic test data generation

### **📋 Next Steps**
1. Test Apple Health Bot with personal export.xml
2. Validate JSON pipeline accuracy
3. Implement cross-format consistency checks
4. Create anonymized sample data for testing 