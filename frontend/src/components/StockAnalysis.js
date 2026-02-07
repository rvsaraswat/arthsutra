import React, { useState } from 'react';
import { 
  Grid, 
  Card, 
  CardContent, 
  CardHeader, 
  Typography, 
  Box, 
  TextField, 
  Button, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper,
  Chip
} from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

// Mock data for stock analysis
const stockData = [
  { symbol: 'RELIANCE', name: 'Reliance Industries', pe: 25.3, roce: 18.5, debtEquity: 0.8, fcfGrowth: 12.5 },
  { symbol: 'TCS', name: 'Tata Consultancy Services', pe: 32.1, roce: 22.3, debtEquity: 0.3, fcfGrowth: 8.7 },
  { symbol: 'HDFCBANK', name: 'HDFC Bank', pe: 18.7, roce: 15.2, debtEquity: 0.6, fcfGrowth: 15.2 },
  { symbol: 'INFY', name: 'Infosys', pe: 28.9, roce: 19.8, debtEquity: 0.4, fcfGrowth: 10.3 },
];

const technicalData = [
  { indicator: 'RSI', value: 62.3, signal: 'Neutral' },
  { indicator: 'MACD', value: 0.02, signal: 'Bullish' },
  { indicator: 'Bollinger Bands', value: 'Bounced', signal: 'Bullish' },
  { indicator: 'Moving Average', value: '20-day: 2450', signal: 'Bullish' },
];

const sentimentData = [
  { source: 'News', score: 0.6, confidence: 0.85 },
  { source: 'Twitter', score: 0.3, confidence: 0.72 },
  { source: 'Analyst Reports', score: 0.8, confidence: 0.91 },
];

const StockAnalysis = () => {
  const [selectedStock, setSelectedStock] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);

  const handleSearch = () => {
    // Mock analysis result
    setAnalysisResult({
      stock: selectedStock,
      fundamentalScore: 0.85,
      technicalScore: 0.72,
      sentimentScore: 0.68,
      overallScore: 0.75,
      recommendation: 'Buy',
      confidence: 0.92
    });
  };

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Stock Analysis
      </Typography>
      
      <Grid container spacing={3}>
        {/* Search Section */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="h2" gutterBottom>
                Analyze Stock
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={8}>
                  <TextField
                    fullWidth
                    label="Stock Symbol"
                    variant="outlined"
                    value={selectedStock}
                    onChange={(e) => setSelectedStock(e.target.value)}
                  />
                </Grid>
                <Grid item xs={4}>
                  <Button 
                    variant="contained" 
                    color="primary" 
                    fullWidth
                    onClick={handleSearch}
                  >
                    Analyze
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Analysis Result */}
        {analysisResult && (
          <Grid item xs={12}>
            <Card>
              <CardHeader 
                title={`Analysis Result for ${analysisResult.stock}`} 
                subheader={`Confidence: ${(analysisResult.confidence * 100).toFixed(0)}%`}
              />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="h6" component="h3" gutterBottom>
                      Scores
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Box>
                        <Typography variant="body1">Fundamental Score: {analysisResult.fundamentalScore}</Typography>
                        <Typography variant="body1">Technical Score: {analysisResult.technicalScore}</Typography>
                        <Typography variant="body1">Sentiment Score: {analysisResult.sentimentScore}</Typography>
                        <Typography variant="h6" component="h4" gutterBottom>
                          Overall Score: {analysisResult.overallScore}
                        </Typography>
                      </Box>
                      <Chip 
                        label={analysisResult.recommendation} 
                        color={analysisResult.recommendation === 'Buy' ? 'success' : 'error'} 
                        variant="outlined" 
                      />
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="h6" component="h3" gutterBottom>
                      Price Prediction Chart
                    </Typography>
                    <ResponsiveContainer width="100%" height={200}>
                      <LineChart
                        data={[
                          { date: '2023-01', price: 2400 },
                          { date: '2023-02', price: 2450 },
                          { date: '2023-03', price: 2500 },
                          { date: '2023-04', price: 2550 },
                          { date: '2023-05', price: 2600 },
                          { date: '2023-06', price: 2650 },
                        ]}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="price" stroke="#1976d2" activeDot={{ r: 8 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}
        
        {/* Fundamental Analysis */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Fundamental Analysis" />
            <CardContent>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Stock</TableCell>
                      <TableCell>PE Ratio</TableCell>
                      <TableCell>ROCE</TableCell>
                      <TableCell>Debt/Equity</TableCell>
                      <TableCell>FCF Growth</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {stockData.map((stock, index) => (
                      <TableRow key={index}>
                        <TableCell>{stock.symbol} - {stock.name}</TableCell>
                        <TableCell>{stock.pe}</TableCell>
                        <TableCell>{stock.roce}%</TableCell>
                        <TableCell>{stock.debtEquity}</TableCell>
                        <TableCell>{stock.fcfGrowth}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Technical Indicators */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Technical Indicators" />
            <CardContent>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Indicator</TableCell>
                      <TableCell>Value</TableCell>
                      <TableCell>Signal</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {technicalData.map((indicator, index) => (
                      <TableRow key={index}>
                        <TableCell>{indicator.indicator}</TableCell>
                        <TableCell>{indicator.value}</TableCell>
                        <TableCell>
                          <Chip 
                            label={indicator.signal} 
                            color={indicator.signal === 'Bullish' ? 'success' : 'default'} 
                            variant="outlined" 
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Sentiment Analysis */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Sentiment Analysis" />
            <CardContent>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Source</TableCell>
                      <TableCell>Sentiment Score</TableCell>
                      <TableCell>Confidence</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {sentimentData.map((source, index) => (
                      <TableRow key={index}>
                        <TableCell>{source.source}</TableCell>
                        <TableCell>{source.score}</TableCell>
                        <TableCell>{source.confidence}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default StockAnalysis;