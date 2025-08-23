# 🧪 Testing Guide - theOrb-web

## Overview

This document describes the comprehensive testing system for theOrb-web that allows testing all functionality **without the GUI** while maintaining the **same database** as the web interface.

## ✅ **Benefits of CLI Testing**

- **🚀 Fast**: No browser or UI overhead
- **🔄 Reproducible**: Consistent test environments  
- **📊 Comprehensive**: Test all features systematically
- **🗄️ Same Database**: Uses identical backend as GUI
- **🤖 Automatable**: Run tests in CI/CD pipelines
- **🔍 Debuggable**: Easy to isolate and fix issues

## 📁 Testing Files

### Core Testing Scripts

| File | Purpose | Usage |
|------|---------|-------|
| `cli_test.py` | Interactive CLI testing interface | `python3 cli_test.py interactive` |
| `automated_tests.py` | Automated test scenarios | `python3 automated_tests.py basic` |
| `quick_test.py` | Fast system validation | `python3 quick_test.py` |

### Test Documentation

| File | Purpose |
|------|---------|
| `TESTING_GUIDE.md` | This guide |
| `test_clip_functionality.py` | CLIP feature validation |
| `test_file_linking.py` | File linking verification |

## 🚀 Quick Start

### 1. Fast System Check
```bash
# Quick validation (30 seconds)
python3 quick_test.py
```

### 2. Interactive Testing
```bash
# Full interactive menu
python3 cli_test.py interactive
```

### 3. Automated Testing
```bash
# Basic functionality test
python3 automated_tests.py basic

# Full system test  
python3 automated_tests.py full

# Performance benchmarks
python3 automated_tests.py performance
```

## 📋 Available Test Commands

### CLI Interactive Mode
```bash
python3 cli_test.py interactive
```

**Main Menu Options:**
- **1. Collection Management** - Create, list, view, delete collections
- **2. Document Processing** - Upload files, process directories  
- **3. Search & Retrieval** - Test search functionality
- **4. CLIP Image Similarity** - Test image search features
- **5. Chat & Conversations** - Test chat functionality
- **6. File Linking & Access** - Verify file access system
- **7. Database Status** - View system status
- **8. Run Full Test Suite** - Comprehensive testing
- **9. Create Test Data** - Generate sample data

### Direct Commands
```bash
# Collection management
python3 cli_test.py collections --create "My Test Collection"

# Search testing  
python3 cli_test.py search --query "machine learning" --collection 1

# View help
python3 cli_test.py --help
```

### Automated Test Scenarios
```bash
# Basic functionality (5-10 minutes)
python3 automated_tests.py basic

# Full system test (15-30 minutes)
python3 automated_tests.py full

# Performance benchmarks (10-20 minutes)  
python3 automated_tests.py performance

# Integration testing (10-15 minutes)
python3 automated_tests.py integration

# Regression testing (5-10 minutes)
python3 automated_tests.py regression

# All scenarios (45-90 minutes)
python3 automated_tests.py all
```

## 🎯 Test Categories

### 1. Collection Management
- ✅ Create/delete collections
- ✅ List collections with stats
- ✅ View collection details
- ✅ Collection metadata handling

### 2. Document Processing
- ✅ Single file upload & processing
- ✅ Multiple file batch upload
- ✅ Directory import functionality
- ✅ File type support (text, images, JSON, markdown)
- ✅ Content extraction and chunking
- ✅ Category and metadata assignment

### 3. Search & Retrieval
- ✅ Vector similarity search
- ✅ Keyword search
- ✅ Category-based filtering
- ✅ File type filtering
- ✅ Cross-collection search
- ✅ Search result ranking

### 4. CLIP Image Similarity
- ✅ Image embedding generation
- ✅ Text-to-image search
- ✅ Image-to-image similarity
- ✅ Image processing pipeline
- ✅ Visual content understanding

### 5. Chat & Conversations
- ✅ Conversation creation/management
- ✅ Message storage and retrieval  
- ✅ AI response generation
- ✅ Context-aware responses
- ✅ Image search in chat

### 6. File Linking & Access
- ✅ File storage system
- ✅ Download URL generation
- ✅ Physical file verification
- ✅ Secure file serving
- ✅ Cross-reference integrity

### 7. System Integration
- ✅ Database operations
- ✅ Vector store integration
- ✅ Model loading (CLIP, embeddings)
- ✅ End-to-end workflows
- ✅ Error handling

## 📊 Test Examples

### Collection Management
```bash
python3 cli_test.py interactive

# Select option 1 (Collection Management)
# Then:
# 1. List Collections - View all collections
# 2. Create Collection - Add new collection
# 3. View Collection Details - Inspect specific collection
# 5. Collection Statistics - Get detailed stats
```

### Document Upload & Processing
```bash
python3 cli_test.py interactive

# Select option 2 (Document Processing)  
# Then:
# 1. Upload Single File - Process one document
# 3. Process Directory - Batch import folder
# 6. Test File Processing - Validate processing pipeline
```

### Search Testing
```bash
python3 cli_test.py interactive

# Select option 3 (Search & Retrieval)
# Then:
# 1. Search in Collection - Test targeted search
# 2. Search Across All Collections - Global search
# 5. Test Vector Similarity - Validate embeddings
```

### Image Similarity
```bash
python3 cli_test.py interactive

# Select option 4 (CLIP Image Similarity)
# Then:
# 1. Search Images by Text - "find red images"
# 2. Upload Image for Similarity - Find similar images
# 5. Test CLIP Embeddings - Validate CLIP processing
```

## 🔧 Advanced Testing

### Custom Test Scenarios

Create your own test scenarios by extending the CLI tester:

```python
from cli_test import OrbCLITester

# Initialize tester
tester = OrbCLITester()

# Create custom collection
collection = tester.create_collection("Custom Test Collection")

# Upload custom files
tester.process_and_upload_file("/path/to/file.pdf", collection)

# Perform custom searches
results = tester.vector_store.search_similar_chunks(
    collection.name, "your query", 5
)

# Validate results
for result in results:
    print(f"Found: {result['metadata']['filename']}")
    print(f"Content: {result['content'][:100]}...")
```

### Performance Testing

Run performance benchmarks:

```bash
# Test with larger datasets
python3 automated_tests.py performance

# View timing results in output:
# 📊 Upload Time: 45.32s (4.53s per file)  
# 📊 Avg Search Time: 0.234s
```

### Integration Testing

Test complete workflows:

```bash
# End-to-end validation
python3 automated_tests.py integration

# Tests:
# - Multi-format document upload
# - Cross-format search
# - AI agent integration  
# - Mixed content conversations
```

## 🗄️ Database Consistency

### Same Database as GUI

The CLI tests use **exactly the same database** as the web GUI:

- **Database**: `sqlite:///orb.db` (same file)
- **Vector Store**: `./chroma_db` (same directory)
- **File Storage**: `./uploads/` (same location)
- **Models**: Same CLIP and embedding models

### Data Sharing

Data created in CLI tests is **immediately available** in the GUI:

1. **Create collection via CLI** → Appears in GUI collections list
2. **Upload documents via CLI** → Searchable in GUI chat
3. **Search via CLI** → Same results as GUI search
4. **File links from CLI** → Downloadable via GUI

### Database Verification

Check database consistency:

```bash
python3 cli_test.py interactive
# Select option 7 (Database Status)

# Shows:
# Collections: 5
# Documents: 23  
# Document Chunks: 156
# Conversations: 8
# Messages: 42
```

## 🛠️ Debugging & Troubleshooting

### Common Issues

**1. Database Connection Errors**
```bash
# Check database file exists
ls -la orb.db

# Test connection
python3 quick_test.py
```

**2. Vector Store Issues**
```bash
# Check vector store directory
ls -la chroma_db/

# Re-initialize if needed
rm -rf chroma_db/
python3 cli_test.py interactive
```

**3. Model Loading Problems**
```bash
# Test CLIP model
python3 test_clip_functionality.py

# Check CUDA/MPS availability
python3 -c "import torch; print(torch.cuda.is_available())"
```

**4. File Processing Errors**
```bash
# Test specific file
python3 cli_test.py interactive
# Select option 2, then 6 (Test File Processing)
```

### Debug Mode

Enable verbose output for debugging:

```bash
# Detailed error messages
python3 automated_tests.py basic --verbose

# Check system status
python3 cli_test.py interactive
# Select option 7 (Database Status)
```

### Log Analysis

Check application logs:

```bash
# Run with debug output
FLASK_ENV=development python3 cli_test.py interactive

# Check for error patterns
grep -i error logs/*.log
```

## 📈 Test Results Interpretation

### Success Indicators

**✅ All Tests Passed**
```
📊 Results: 8/8 tests passed
🎉 All systems operational!
```

**⚠️ Partial Success**
```
📊 Results: 6/8 tests passed  
⚠️ Mostly working, minor issues
```

**❌ Major Issues**
```
📊 Results: 3/8 tests passed
🚨 Major issues detected
```

### Performance Benchmarks

**Good Performance:**
- Document processing: < 5s per file
- Search queries: < 1s average
- CLIP processing: < 2s per image
- Vector operations: < 0.5s

**Performance Issues:**
- Document processing: > 15s per file
- Search queries: > 3s average  
- Memory usage: > 4GB
- Disk usage growing rapidly

## 🔄 Continuous Testing

### Development Workflow

1. **Quick Check** - `python3 quick_test.py` (30s)
2. **Feature Testing** - `python3 cli_test.py interactive` (5-15min)
3. **Full Validation** - `python3 automated_tests.py full` (30min)

### Before Deployment

1. **Regression Tests** - `python3 automated_tests.py regression`
2. **Performance Tests** - `python3 automated_tests.py performance`  
3. **Integration Tests** - `python3 automated_tests.py integration`

### CI/CD Integration

```yaml
# Example GitHub Actions workflow
- name: Run Quick Tests
  run: python3 quick_test.py

- name: Run Basic Tests  
  run: python3 automated_tests.py basic

- name: Run Regression Tests
  run: python3 automated_tests.py regression
```

## 📚 Test Data Management

### Creating Test Data

```bash
python3 cli_test.py interactive
# Select option 9 (Create Test Data)

# Creates:
# - Test collection with sample documents
# - Sample images with CLIP processing
# - Test conversations and messages
```

### Cleaning Test Data

```bash
# Clean up after tests
python3 automated_tests.py basic --cleanup

# Manual cleanup via CLI
python3 cli_test.py interactive
# Delete specific collections via option 1
```

### Test Data Isolation

Test data is clearly labeled:
- Collections: "Test Collection", "Basic Test Collection" 
- Conversations: "Test Automated Chat"
- Files: Stored in temporary directories

## 🎉 Conclusion

The theOrb-web testing system provides **comprehensive validation** of all functionality without requiring the GUI interface. It uses the **same database and backend** as the web application, ensuring **perfect consistency** between testing and production environments.

### Key Benefits:

- ✅ **Complete Coverage** - Every feature is testable
- ⚡ **Fast Execution** - No UI overhead
- 🔄 **Reproducible** - Consistent test environments
- 🤖 **Automatable** - Perfect for CI/CD
- 🗄️ **Database Consistency** - Same data as GUI
- 🔍 **Easy Debugging** - Isolated component testing

### Getting Started:

1. **Start with quick test**: `python3 quick_test.py`
2. **Explore interactively**: `python3 cli_test.py interactive`  
3. **Run automated suite**: `python3 automated_tests.py basic`
4. **Verify in GUI**: Open web interface and see your test data

**Happy Testing!** 🧪✨