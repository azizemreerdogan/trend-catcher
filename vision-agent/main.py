import argparse
from orchestrator import run_pipeline

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TrendCatcher Agent Orchestrator")
    parser.add_argument("video_id", type=str, nargs="?", default="video", 
                        help="The video ID (folder name inside catcher-data) to analyze")
    
    args = parser.parse_args()
    run_pipeline(args.video_id)
