# Crowdin Integration Setup Guide

This guide will help you set up Crowdin integration with your Libriya project for managing translations.

## Why Crowdin?

Crowdin is a cloud-based localization management platform that offers:
- **Free plan with full API access** (unlike Lokalise)
- **GitHub integration** for automatic sync
- **Collaborative translation** with an intuitive web interface
- **Translation memory** and glossary support
- **Quality checks** and validation

## Prerequisites

You mentioned you've already:
- ✅ Created a Crowdin project
- ✅ Set up GitHub integration

Great! Let's complete the setup.

## Step 1: Configure Crowdin Project Settings

1. **Go to your Crowdin project** at [crowdin.com](https://crowdin.com)
2. **Navigate to Settings → Files**
3. **Verify your source language** is set to English (en)
4. **Add target languages:**
   - Polish (pl)
   - Any other languages you want to support
5. **File format:** Should be "Gettext PO" (automatic detection usually works)

## Step 2: Get Your Crowdin Credentials

### 2.1 Personal Access Token

1. Click on your **profile picture** (top right)
2. Go to **Settings → API**
3. Click **New Token**
4. Give it a name (e.g., "GitHub Actions - Libriya")
5. Select these scopes:
   - ✅ `project` - Full access to projects
   - ✅ `glossary` - Access to glossary (optional but recommended)
   - ✅ `tm` - Access to translation memory (optional but recommended)
6. Click **Create**
7. **Copy the token** (you won't see it again!)

### 2.2 Project ID

1. Go to your Crowdin project
2. The Project ID is in the URL: `crowdin.com/project/YOUR-PROJECT-NAME`
3. Or find it in **Project Settings → API → Project ID**

## Step 3: Add GitHub Secrets

1. Go to your **GitHub repository**
2. Navigate to **Settings → Secrets and variables → Actions**
3. Click **"New repository secret"** and add:
   - **Name:** `CROWDIN_PERSONAL_TOKEN`
   - **Value:** Your Personal Access Token from Step 2.1
4. Click **"New repository secret"** again and add:
   - **Name:** `CROWDIN_PROJECT_ID`
   - **Value:** Your Project ID from Step 2.2

**Important:** The `crowdin.yml` file references these environment variables, so the names must match exactly.

## Step 4: Configure GitHub Integration in Crowdin

Since you mentioned you've already set up the GitHub integration, verify these settings:

1. In Crowdin, go to **Integrations → GitHub**
2. Click on your integration to configure it
3. **Repository:** Should point to `MarcinSachs/Libriya`
4. **Configuration file:** `crowdin.yml` (in the root directory)
5. **Service branch:** `main` (or your default branch)

### Sync Settings

Configure what triggers synchronization:

- ✅ **Source files** - Push sources to Crowdin when they change in GitHub
- ✅ **Translations** - Create a PR in GitHub when translations are updated
- ✅ **Branches** - Sync with `main` branch (or specify others)

### PR Settings (Recommended)

- **PR title:** `[Crowdin] Update translations`
- **PR branch:** `l10n_main` (Crowdin default) or `crowdin/translations-update`
- **Labels:** Add `translations` or `i18n` label (optional)

## Step 5: Upload Initial Translations

The `crowdin.yml` file is configured to sync files automatically, but you may want to upload your existing translations for the first time:

### Option A: Automatic Upload (Recommended)

1. Commit the `crowdin.yml` file to your repository
2. Push to the `main` branch
3. Crowdin will automatically detect and upload:
   - `translations/messages.pot` (source template)
   - `translations/en/LC_MESSAGES/messages.po` (English)
   - `translations/pl/LC_MESSAGES/messages.po` (Polish)

### Option B: Manual Upload (If needed)

1. In Crowdin, go to **Sources → Files**
2. Click **Upload Files**
3. Upload `translations/messages.pot`
4. Crowdin will detect it as Gettext PO format
5. Existing translations in `translations/pl/LC_MESSAGES/messages.po` will be automatically matched

## Step 6: Test the Integration

### Test 1: Push Source Changes (GitHub → Crowdin)

1. Make a change to a translation string in your code
2. Extract new strings:
   ```bash
   pybabel extract -F babel.cfg -o translations/messages.pot .
   pybabel update -i translations/messages.pot -d translations
   ```
3. Commit and push to `main`:
   ```bash
   git add translations/
   git commit -m "Update translation strings"
   git push
   ```
4. Check Crowdin - new strings should appear within a few minutes

### Test 2: Pull Translations (Crowdin → GitHub)

1. In Crowdin, edit a translation (e.g., change a Polish string)
2. Click **Save**
3. Crowdin will automatically create a Pull Request in GitHub
4. Review and merge the PR
5. Your translations are now updated!

## Working with Translations

### Daily Workflow

1. **Developers:** Add translatable strings in Flask code using `gettext()` or `_()`
   ```python
   from flask_babel import gettext as _
   message = _("Hello, world!")
   ```

2. **Extract new strings:**
   ```bash
   pybabel extract -F babel.cfg -o translations/messages.pot .
   ```

3. **Update translation files:**
   ```bash
   pybabel update -i translations/messages.pot -d translations
   ```

4. **Commit and push:**
   ```bash
   git add translations/
   git commit -m "Extract new translation strings"
   git push
   ```

5. **Crowdin syncs automatically** (usually within 5-10 minutes)

6. **Translators work in Crowdin** web interface

7. **Crowdin creates PR** when translations are ready

8. **Review and merge PR** to get translations back

9. **Compile translations:**
   ```bash
   python compile_translations.py
   # or
   pybabel compile -d translations
   ```

### Commands Reference

```bash
# Extract translatable strings from source code
pybabel extract -F babel.cfg -o translations/messages.pot .

# Update existing .po files with new strings
pybabel update -i translations/messages.pot -d translations

# Initialize a new language (if adding a new one)
pybabel init -i translations/messages.pot -d translations -l <language_code>

# Compile .po files to .mo files (required for Flask to use them)
pybabel compile -d translations
# or use the helper script
python compile_translations.py
```

## File Structure

```
Libriya/
├── crowdin.yml                    # Crowdin configuration
├── babel.cfg                      # Babel extractor configuration
├── translations/
│   ├── messages.pot              # Translation template (source)
│   ├── en/
│   │   └── LC_MESSAGES/
│   │       ├── messages.po       # English translations
│   │       └── messages.mo       # Compiled English (generated)
│   └── pl/
│       └── LC_MESSAGES/
│           ├── messages.po       # Polish translations
│           └── messages.mo       # Compiled Polish (generated)
```

## Crowdin Features

### Translation Memory
Crowdin automatically remembers previous translations and suggests them for similar strings, speeding up translation work.

### Glossary
Create a project glossary to ensure consistent translation of key terms:
1. Go to **Glossary** in Crowdin
2. Add terms like "Library", "Book", "Loan", etc.
3. Translators will see these when translating

### Quality Checks
Crowdin automatically checks for:
- Missing placeholders (e.g., `%s`, `{variable}`)
- Inconsistent punctuation
- Leading/trailing spaces
- Length issues

### Proofreading
Enable proofreading workflow:
1. **Settings → Workflow**
2. Enable **Proofreading** step
3. Assign proofreaders who review translations before they're sent back to GitHub

## Troubleshooting

### Crowdin Not Syncing from GitHub

**Check:**
1. GitHub integration is properly configured in Crowdin
2. `crowdin.yml` is in the repository root
3. File paths in `crowdin.yml` match your actual file structure
4. GitHub secrets are set correctly

**Solution:**
- Go to Crowdin → Integrations → GitHub → Click "Sync Now"
- Check integration logs for errors

### Translations Not Creating PR

**Check:**
1. Crowdin has permission to create PRs in your repository
2. PR settings are configured in Crowdin integration
3. There are actually new translations to sync

**Solution:**
- Verify GitHub App permissions
- Manually trigger sync in Crowdin

### File Format Issues

**Error:** "File format not recognized"

**Solution:**
- Ensure files are valid Gettext PO format
- Check for syntax errors in .po files
- Verify the `type: gettext` setting in `crowdin.yml`

### Merge Conflicts

If Crowdin PR has merge conflicts:
1. Manually merge the `main` branch into the Crowdin branch:
   ```bash
   git fetch origin
   git checkout l10n_main  # or your Crowdin branch name
   git merge main
   git push
   ```
2. Or ask Crowdin to recreate the PR with fresh changes

## Advanced Configuration

### Adding More Languages

1. **In Crowdin:**
   - Settings → Target Languages → Add language
   
2. **In your repository:**
   ```bash
   pybabel init -i translations/messages.pot -d translations -l <language_code>
   ```
   
3. **Update `config.py`:**
   ```python
   LANGUAGES = ['en', 'pl', 'de']  # Add new language codes
   ```

4. Push changes - Crowdin will detect the new language structure

### Branch Management

To sync translations for feature branches:

1. **In `crowdin.yml`:**
   ```yaml
   # Add after existing configuration
   branches:
     - name: main
       title: Main Branch
     - name: develop
       title: Development Branch
   ```

2. **In Crowdin integration settings:**
   - Add the branches you want to sync

## Resources

- [Crowdin Documentation](https://support.crowdin.com/)
- [Crowdin GitHub Integration Guide](https://support.crowdin.com/github-integration/)
- [Crowdin Configuration File Reference](https://support.crowdin.com/configuration-file/)
- [Flask-Babel Documentation](https://python-babel.github.io/flask-babel/)

## Support

If you encounter issues:
1. Check Crowdin integration logs in your project
2. Review GitHub Actions logs (if using workflows)
3. Check [Crowdin Support Center](https://support.crowdin.com/)
4. Open an issue in this repository

## Migration from Lokalise

You're migrating from Lokalise, so here are the key differences:

| Feature | Lokalise | Crowdin |
|---------|----------|---------|
| **Free Plan API** | Limited (no file upload) | Full access ✅ |
| **GitHub Integration** | Via GitHub Actions | Native integration ✅ |
| **Configuration** | In workflow files | `crowdin.yml` file |
| **Sync Method** | Manual/scheduled workflows | Automatic on push ✅ |
| **PR Creation** | Via workflow | Automatic ✅ |

**Benefits of Crowdin:**
- ✅ No need for GitHub Actions workflows
- ✅ Automatic bidirectional sync
- ✅ Real-time updates (within minutes)
- ✅ Built-in GitHub integration
- ✅ Free plan includes all essential features

Welcome to Crowdin! 🎉
