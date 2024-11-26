parser = argparse.ArgumentParser(description='Stock Analysis and Trading Application')
parser.add_argument('--generate', type=str, choices=['true', 'false'], help='Generate stock analysis report if true')
parser.add_argument('--full', type=str, choices=['true', 'false'], default='false', help='Fetch all symbols if true')
args = parser.parse_args()

if args.generate and args.generate.lower() == 'true':
    all_data = args.full.lower() == 'true'
    print(f"Generating stock analysis report with full data: {all_data}")
    generate_stock_analysis(allData=all_data)
else:
    print("Starting backend server...")
    app.run(host='0.0.0.0', port=5000)