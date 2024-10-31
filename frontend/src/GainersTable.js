import React from 'react';
import { Table, Button, Tooltip } from 'antd';

const GainersTable = ({ gainers, isScrapingStarted, selectedGainer, startScraping }) => {
    const dataSource = gainers.map((gainer, index) => ({
        key: index,
        symbol: gainer.symbol,
        last_price: gainer.stock_info.last_price, // Corrected
        price_high: gainer.stock_info.price_high, // Corrected
        price_low: gainer.stock_info.price_low, // Corrected
        price_prev_close: gainer.stock_info.price_prev_close, // Corrected
        gain: gainer.stock_info.gain, // Corrected
        change: gainer.change,
        pivotPoints: gainer.stock_info.pivot_points,
        position: gainer.stock_info.position,
    }));

    const columns = [
        {
            title: 'Symbol',
            dataIndex: 'symbol',
            key: 'symbol',
        },
        {
            title: 'High Price',
            dataIndex: 'price_high',
            key: 'price_high',
        },
        {
            title: 'Low Price',
            dataIndex: 'price_low',
            key: 'price_low',
        },
        {
            title: 'Last Price',
            dataIndex: 'last_price',
            key: 'last_price',
        },
        {
            title: 'Previous Price',
            dataIndex: 'price_prev_close',
            key: 'price_prev_close',
        },
        {
            title: 'Changes',
            dataIndex: 'gain',
            key: 'gain',
        },
        {
            title: 'Gain',
            dataIndex: 'change',
            key: 'change',
        },
        {
            title: 'Position',
            dataIndex: 'position',
            key: 'position',
            render: (text) => (
                <Tooltip title={text} placement="topLeft">
                    <span className="max-w-[120px] block overflow-hidden text-ellipsis whitespace-nowrap rounded-full bg-blue-500 text-white px-2">
                        {text}
                    </span>
                </Tooltip>
            ),
        },
        {
            title: 'Action',
            key: 'action',
            render: (_, record) => (
                <Button
                    onClick={() => startScraping(record.symbol)}
                    disabled={isScrapingStarted}
                    className="bg-green-500 text-white"
                    loading={isScrapingStarted && selectedGainer === record.symbol}
                >
                    {isScrapingStarted && selectedGainer === record.symbol ? 'Scraping...' : 'Start Scraping'}
                </Button>
            ),
        },
    ];

    const expandedRowRender = (record) => (
        <div className="p-4">
            <p className="font-semibold">Pivot Points:</p>
            <p className="rounded-full bg-blue-500 text-white px-2">PP: {record.pivotPoints.pp}</p>
            <div className="grid grid-cols-2 gap-4">
                <div>
                    <p className="font-semibold">Resistance Levels:</p>
                    <p className="rounded-full bg-red-500 text-white px-2">R1: {record.pivotPoints.r1}</p>
                    <p className="rounded-full bg-red-500 text-white px-2">R2: {record.pivotPoints.r2}</p>
                    <p className="rounded-full bg-red-500 text-white px-2">R3: {record.pivotPoints.r3}</p>
                </div>
                <div>
                    <p className="font-semibold">Support Levels:</p>
                    <p className="rounded-full bg-green-500 text-white px-2">S1: {record.pivotPoints.s1}</p>
                    <p className="rounded-full bg-green-500 text-white px-2">S2: {record.pivotPoints.s2}</p>
                    <p className="rounded-full bg-green-500 text-white px-2">S3: {record.pivotPoints.s3}</p>
                </div>
            </div>
        </div>
    );

    return (
        <div className="mb-6">
            <hr className="flex-grow border-t border-dashed border-gray-400 mb-4" />
            <h2 className="text-2xl font-bold mb-4">Top Gainers</h2>
            <Table
                dataSource={dataSource}
                columns={columns}
                pagination={false}
                bordered
                expandable={{
                    expandedRowRender,
                    rowExpandable: (record) => true,
                }}
            />
        </div>
    );
};

export default GainersTable;
