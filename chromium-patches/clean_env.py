import os
import sys

def clean_environment_paths():
    github_env = os.environ.get('GITHUB_ENV')
    for key in ['INCLUDE', 'LIB']:
        if key in os.environ:
            parts = [p.strip() for p in os.environ[key].split(';') if p.strip()]
            valid_parts = [p for p in parts if os.path.exists(p)]
            cleaned = ';'.join(valid_parts)
            os.environ[key] = cleaned
            print(f"[CleanEnv] {key}: kept {len(valid_parts)} of {len(parts)} paths.")
            if github_env:
                try:
                    with open(github_env, 'a', encoding='utf-8') as f:
                        f.write(f"{key}={cleaned}\n")
                    print(f"[CleanEnv] Written to GITHUB_ENV: {key}")
                except Exception as e:
                    print(f"[CleanEnv] Warning: could not write to GITHUB_ENV: {e}")

if __name__ == '__main__':
    clean_environment_paths()
