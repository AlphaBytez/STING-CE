# 🏺 Honey Reserve Management Guide

## What is Honey Reserve?

Your **Honey Reserve** is your personal storage allocation within STING - like a bee's personal honey storage. Each user receives 1GB of space to store:

- 📎 Temporary chat uploads
- 🍯 Personal honey jar documents  
- 📊 Generated reports and exports
- 🖼️ Screenshots and images

## Viewing Your Honey Reserve

### Dashboard Widget

Navigate to your dashboard to see:
- **Visual Meter**: 🏺 icon showing fill percentage
- **Usage Breakdown**: Pie chart by category
- **Quick Stats**: Files count and largest files

### Detailed View

Click "Manage Honey Reserve" for:
- File-by-file listing
- Sort by size, date, or type
- Bulk selection tools
- Storage trends over time

## Storage Categories

### Temporary Uploads (Auto-cleanup)
- **Retention**: 24-48 hours
- **Purpose**: Chat session analysis
- **Auto-delete**: Yes
- **Icon**: 🕐

### Honey Jar Documents (Permanent)
- **Retention**: Until manually deleted
- **Purpose**: Knowledge base building
- **Auto-delete**: No
- **Icon**: 🍯

### Generated Reports (30 days)
- **Retention**: 30 days
- **Purpose**: Exported data and analytics
- **Auto-delete**: After 30 days
- **Icon**: 📊

### Personal Workspace (Permanent)
- **Retention**: Until manually deleted
- **Purpose**: Personal notes and drafts
- **Auto-delete**: No
- **Icon**: 📝

## Managing Your Storage

### Automatic Cleanup

STING automatically manages your Honey Reserve:

1. **Temporary Files**: Deleted after retention period
2. **Old Reports**: Cleaned up after 30 days
3. **Warning at 90%**: Email notification
4. **Full Reserve**: Oldest temporary files deleted first

### Manual Cleanup

To free up space:

1. **Review Large Files**
   ```
   Dashboard → Honey Reserve → Sort by Size
   ```

2. **Bulk Delete**
   - Select multiple files
   - Click "Delete Selected"
   - Confirm deletion

3. **Export Before Deleting**
   - Download important files
   - Create backups
   - Then safely delete

## Storage Best Practices

### Optimize Your Usage

1. **Regular Reviews**
   - Monthly storage check
   - Remove duplicate files
   - Archive old documents

2. **Smart Uploading**
   - Compress large files before upload
   - Use appropriate file formats
   - Avoid uploading duplicates

3. **Organize Efficiently**
   - Use honey jars for shared documents
   - Keep personal drafts in workspace
   - Let temporary files auto-cleanup

### What Counts Against Your Quota?

✅ **Counted**:
- All uploaded files
- Generated reports
- File versions/history
- Encrypted backups

❌ **Not Counted**:
- Shared honey jar files (counted against owner)
- System documentation
- Thumbnails and previews
- Metadata and indexes

## Quota Warnings

### Warning Levels

| Level | Reserve Used | Action |
|-------|--------------|---------|
| 🟢 Normal | 0-75% | No action needed |
| 🟡 Warning | 75-90% | Email notification |
| 🟠 Critical | 90-95% | Daily notifications |
| 🔴 Full | 95-100% | Upload restrictions |

### When Reserve is Full

If your Honey Reserve reaches capacity:
1. New uploads are blocked
2. Temporary files are auto-deleted
3. You receive immediate notification
4. Admin assistance available

## Requesting More Storage

### Standard Process

1. Contact your administrator
2. Provide justification:
   - Current usage patterns
   - Business needs
   - Expected growth

3. Admin can increase via:
   ```yaml
   users:
     user@example.com:
       honey_reserve_quota: 2147483648  # 2GB
   ```

### Temporary Increases

For special projects:
- Request temporary quota boost
- Specify duration needed
- Automatic revert after period

## API Access

### Check Usage Programmatically

```bash
# Get current usage
curl -X GET https://sting.local/api/user/honey-reserve \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "total_bytes": 1073741824,
  "used_bytes": 536870912,
  "percentage": 50,
  "breakdown": {
    "temporary": 104857600,
    "honey_jars": 432013312,
    "reports": 0
  }
}
```

### Manage Files via API

```bash
# List files
GET /api/user/honey-reserve/files

# Delete file
DELETE /api/user/honey-reserve/files/{file_id}

# Bulk delete
POST /api/user/honey-reserve/bulk-delete
{
  "file_ids": ["id1", "id2", "id3"]
}
```

## Storage Analytics

### Usage Reports

Monthly reports show:
- Storage trends
- File type distribution  
- Upload patterns
- Cleanup effectiveness

### Optimization Tips

Based on your usage:
- "Consider archiving large PDFs"
- "20% of files are duplicates"
- "Reports older than 14 days unused"

## Troubleshooting

### Common Issues

**"Insufficient storage" error**
- Check Honey Reserve dashboard
- Delete temporary files
- Clear old reports

**Files not appearing in usage**
- Allow 5 minutes for sync
- Refresh the dashboard
- Check file processing status

**Quota shows incorrect value**
- Run storage recalculation
- Contact admin for audit
- Check for stuck uploads

### Emergency Cleanup

If urgently need space:
1. Go to Honey Reserve → Emergency Cleanup
2. Select "Delete all temporary files"
3. Confirm action
4. Instantly frees temporary storage

## Privacy & Data Control

### Your Rights

- **Data Export**: Download all files anytime
- **Deletion**: Permanent deletion available
- **Audit Log**: See who accessed your files
- **Encryption**: All files encrypted with your key

### Data Retention

| Type | Default | Configurable |
|------|---------|--------------|
| Temporary | 48 hours | 24-168 hours |
| Reports | 30 days | 7-90 days |
| Honey Jars | Forever | Admin policy |
| Audit Logs | 90 days | 30-365 days |

---

*Your Honey Reserve is your personal space in STING. Use it wisely, and it will serve you well! 🐝*