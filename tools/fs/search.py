import os
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def findFiles(fileName: str, searchDir: str = "~") -> list:
    """Searches for file or folder by name recursively. Returns list of matching absolute paths"""
    logging.info(f"Searching for {fileName} in {searchDir}")

    baseDir = os.path.expanduser(searchDir)

    if not os.path.exists(baseDir):
        return [f"Error: Directory {searchDir} does not exist."]
    
    matches = []

    try:
        for root, dirs, files in os.walk(baseDir):
            for file in files:
                if fileName.lower() in file.lower():
                    matches.append(os.path.join(root, file))
                    if len(matches) >= 5:
                        return matches
                    
            for d in dirs:
                if fileName.lower() in d.lower():
                    matches.append(os.path.join(root, d))
                    if len(matches) >= 5:
                        return matches
                    
    except Exception as e:
        logging.error(f"Search failed : {e}")
        return [f"Error during search : {e}"]
    
    if not matches:
        return [f"No files or folders found matching '{fileName}"]
    
    return matches


def readFile(filePath: str) -> str:
    """Reads the contents of a text file. Useful for reading notes, scripts or config file"""
    logging.info(f"Reading file: {filePath}")
    expandedPath = os.path.expanduser(filePath)

    if not os.path.exists(expandedPath):
        return f"Error : file {filePath} does not exist"
    

    try:
        with open(expandedPath, 'r', encoding = 'utf-8') as f:
            content = f.read(2000)
            if len(content) == 2000:
                content += "\n....[TRUNCATED FOR LENGTH]"
            return content
        
    except UnicodeDecodeError:
        return "Error: File is not a readable text file (might be a binary or image)."
    
    except Exception as e:
        return f"Error reading file: {e}"


if __name__ == "__main__":
    print("Testing File system tools....")

    print("\nSearching for main.py in ~/Documents/Fun/l.o.om.")
    results = findFiles("main.py", "~/Documents/Fun/l.o.o.m.")
    print(results)

    if results and not results[0].startswith("Error") and not results[0].startswith("No files"):
        print(f"\nReading first matched file: {results[0]}")
        print(readFile(results[0]))